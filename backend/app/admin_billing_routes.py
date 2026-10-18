import csv
import io
import re
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, make_response, request

from . import billing, billing_rules as rules
from .extensions import db
from .models import AuditLog, DiscountCode, Enrollment, Path, Payment, Refund, User
from .audit import audit
from .security import admin_required

bp = Blueprint("admin_billing", __name__, url_prefix="/api/admin")
CODE_RE = re.compile(r"^[A-Z0-9_-]{3,32}$")


def _int(value, name, lo=None, hi=None):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a whole number.")
    try:
        n = int(value)
        if float(value) != n:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a whole number.")
    if lo is not None and n < lo:
        raise ValueError(f"{name} must be at least {lo}.")
    if hi is not None and n > hi:
        raise ValueError(f"{name} must be at most {hi}.")
    return n


def _date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Dates must look like 2026-12-31.")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _code_dict(c, used):
    return {
        "id": c.id, "code": c.code, "description": c.description, "kind": c.kind, "value": c.value,
        "path": c.path.slug if c.path else None, "user_email": c.user_email, "max_redemptions": c.max_redemptions,
        "used": used, "valid_until": c.valid_until.isoformat() if c.valid_until else None, "active": c.active,
    }


@bp.get("/payments")
@admin_required
def list_payments():
    q = Payment.query.join(User, User.id == Payment.user_id)
    status = request.args.get("status")
    if status:
        q = q.filter(Payment.status == status)
    s = (request.args.get("q") or "").strip().lower()
    if s:
        like = f"%{s}%"
        q = q.filter(db.or_(db.func.lower(User.email).like(like), db.func.lower(User.name).like(like), db.func.lower(Payment.mpesa_receipt).like(like)))
    rows = q.order_by(Payment.created_at.desc()).limit(200).all()
    return jsonify(payments=[{**p.to_dict(), "learner": p.user.name, "email": p.user.email, "path": p.path.level} for p in rows])


@bp.post("/payments/manual")
@admin_required
def manual_payment():
    body = request.get_json(silent=True) or {}
    user = db.session.get(User, body.get("user_id") or 0)
    if user is None:
        return jsonify(error="Learner not found."), 404
    try:
        amount = _int(body.get("amount"), "Amount", 1, 1_000_000)
        p = billing.record_manual(g.user, user, amount, body.get("note") or "Cash / bank payment")
    except (ValueError, billing.PaymentError) as exc:
        return jsonify(error=str(exc)), 400
    audit(g.user, "payment.manual", f"user:{user.id}", f"KES {amount}: {body.get('note') or ''}")
    return jsonify(payment=p.to_dict())


@bp.get("/discounts")
@admin_required
def list_discounts():
    used = dict(db.session.query(Enrollment.discount_code_id, db.func.count(Enrollment.id)).filter(Enrollment.discount_code_id.isnot(None)).group_by(Enrollment.discount_code_id).all())
    codes = DiscountCode.query.order_by(DiscountCode.created_at.desc()).all()
    return jsonify(discounts=[_code_dict(c, used.get(c.id, 0)) for c in codes])


@bp.post("/discounts")
@admin_required
def create_discount():
    b = request.get_json(silent=True) or {}
    code = (b.get("code") or "").strip().upper()
    kind = b.get("kind")
    try:
        if not CODE_RE.match(code):
            raise ValueError("Code must be 3-32 letters, numbers, - or _.")
        if kind not in ("percent", "fixed"):
            raise ValueError("Choose percent or fixed.")
        value = _int(b.get("value"), "Value", 1, 100 if kind == "percent" else 1_000_000)
        max_r = _int(b["max_redemptions"], "Maximum uses", 1) if b.get("max_redemptions") not in (None, "") else None
        valid_until = _date(b.get("valid_until"))
        path = None
        if b.get("path"):
            path = Path.query.filter_by(slug=b["path"]).first()
            if path is None:
                raise ValueError("Unknown path.")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    if DiscountCode.query.filter_by(code=code).first():
        return jsonify(error="That code already exists."), 409
    email = (b.get("user_email") or "").strip().lower() or None
    c = DiscountCode(code=code, description=(b.get("description") or "")[:200], kind=kind, value=value,
                     path_id=path.id if path else None, user_email=email, max_redemptions=max_r,
                     valid_until=valid_until, active=True, created_by=g.user.id)
    db.session.add(c)
    db.session.commit()
    audit(g.user, "discount.create", f"code:{code}", f"{kind} {value}, max uses {max_r}, path {b.get('path') or 'any'}")
    return jsonify(discount=_code_dict(c, 0)), 201


@bp.patch("/discounts/<int:code_id>")
@admin_required
def update_discount(code_id):
    c = db.session.get(DiscountCode, code_id)
    if c is None:
        return jsonify(error="Not found."), 404
    b = request.get_json(silent=True) or {}
    try:
        if "active" in b:
            c.active = bool(b["active"])
        if "description" in b:
            c.description = (b["description"] or "")[:200]
        if "max_redemptions" in b:
            c.max_redemptions = _int(b["max_redemptions"], "Maximum uses", 1) if b["max_redemptions"] not in (None, "") else None
        if "valid_until" in b:
            c.valid_until = _date(b["valid_until"])
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    db.session.commit()
    audit(g.user, "discount.update", f"code:{c.code}", str(b))
    used = Enrollment.query.filter_by(discount_code_id=c.id).count()
    return jsonify(discount=_code_dict(c, used))


@bp.patch("/paths/<slug>")
@admin_required
def update_price(slug):
    p = Path.query.filter_by(slug=slug).first_or_404()
    try:
        p.price_kes = _int((request.get_json(silent=True) or {}).get("price_kes"), "Price", 0, 1_000_000)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    db.session.commit()
    audit(g.user, "price.change", f"path:{slug}", f"KES {p.price_kes}")
    return jsonify(path=p.summary())


@bp.post("/learners/<int:user_id>/discount")
@admin_required
def learner_discount(user_id):
    """Give one learner a discount or scholarship (replaces any earlier discount). amount 0 clears it."""
    user = db.session.get(User, user_id)
    if user is None or not user.path_id:
        return jsonify(error="Learner not found or has no path."), 404
    b = request.get_json(silent=True) or {}
    e = billing.get_enrollment(user)
    try:
        if b.get("percent") not in (None, ""):
            amount = rules.discount_amount(e.price_kes, "percent", _int(b["percent"], "Percent", 0, 100))
        else:
            amount = rules.discount_amount(e.price_kes, "fixed", _int(b.get("amount"), "Amount", 0, 1_000_000))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    e.discount_kes = amount
    e.discount_code_id = None
    e.discount_note = (b.get("reason") or ("Admin discount" if amount else ""))[:300]
    db.session.commit()
    audit(g.user, "learner.discount", f"user:{user.id}", f"KES {amount}: {e.discount_note}")
    return jsonify(billing=billing.billing_state(user))


# ----------------------------------------------------------------------------- refunds
def _refund_row(r):
    return {**r.to_dict(), "learner": r.user.name, "email": r.user.email, "path": r.path.level, "user_id": r.user_id}


@bp.get("/refunds")
@admin_required
def list_refunds():
    q = Refund.query
    status = request.args.get("status")
    if status:
        q = q.filter(Refund.status == status)
    rows = q.order_by(Refund.created_at.desc()).limit(200).all()
    return jsonify(refunds=[_refund_row(r) for r in rows])


def _refund_action(refund_id, fn, action="refund"):
    r = db.session.get(Refund, refund_id)
    if r is None:
        return jsonify(error="Refund not found."), 404
    try:
        fn(r)
    except (billing.RefundError, ValueError) as exc:
        return jsonify(error=str(exc)), 400
    audit(g.user, f"refund.{action}", f"refund:{r.id}", f"user:{r.user_id} KES {r.approved_amount if r.approved_amount is not None else r.requested_amount} {r.admin_note or ''}")
    return jsonify(refund=_refund_row(r))


@bp.post("/refunds/<int:refund_id>/approve")
@admin_required
def approve_refund(refund_id):
    b = request.get_json(silent=True) or {}
    return _refund_action(refund_id, lambda r: billing.approve_refund(g.user, r, _int(b.get("amount", r.eligible_amount or r.requested_amount), "Amount", 1, 1_000_000), b.get("note") or ""), "approve")


@bp.post("/refunds/<int:refund_id>/reject")
@admin_required
def reject_refund(refund_id):
    b = request.get_json(silent=True) or {}
    return _refund_action(refund_id, lambda r: billing.reject_refund(g.user, r, b.get("note") or ""), "reject")


@bp.post("/refunds/<int:refund_id>/paid-out")
@admin_required
def refund_paid_out(refund_id):
    b = request.get_json(silent=True) or {}
    return _refund_action(refund_id, lambda r: billing.mark_refund_paid(g.user, r, b.get("method") or "M-Pesa", b.get("reference") or ""), "paid_out")


@bp.post("/refunds")
@admin_required
def create_refund():
    b = request.get_json(silent=True) or {}
    user = db.session.get(User, b.get("user_id") or 0)
    if user is None:
        return jsonify(error="Learner not found."), 404
    try:
        r = billing.admin_create_refund(g.user, user, _int(b.get("amount"), "Amount", 1, 1_000_000), b.get("reason") or "")
    except (billing.RefundError, ValueError) as exc:
        return jsonify(error=str(exc)), 400
    audit(g.user, "refund.create", f"refund:{r.id}", f"user:{user.id} KES {r.approved_amount}")
    return jsonify(refund=_refund_row(r)), 201


# ----------------------------------------------------------------------------- activity log, exports, reconcile
@bp.get("/audit")
@admin_required
def audit_list():
    q = AuditLog.query
    action = (request.args.get("action") or "").strip()
    if action:
        q = q.filter(AuditLog.action.like(f"{action}%"))
    rows = q.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify(entries=[{"id": a.id, "who": a.admin.name if a.admin else "system", "action": a.action, "target": a.target, "detail": a.detail, "at": a.created_at.isoformat()} for a in rows])


def _csv_response(filename, header, rows):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(header)
    for row in rows:
        w.writerow([rules.csv_safe(c) for c in row])
    resp = make_response(out.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@bp.get("/payments.csv")
@admin_required
def payments_csv():
    rows = Payment.query.join(User, User.id == Payment.user_id).order_by(Payment.created_at.desc()).limit(5000).all()
    return _csv_response("payments.csv", ["id", "date", "learner", "email", "path", "amount_kes", "method", "status", "mpesa_receipt", "note"],
                         [[p.id, p.created_at.isoformat(), p.user.name, p.user.email, p.path.level, p.amount, p.method, p.status, p.mpesa_receipt, p.note] for p in rows])


@bp.get("/refunds.csv")
@admin_required
def refunds_csv():
    rows = Refund.query.order_by(Refund.created_at.desc()).limit(5000).all()
    return _csv_response("refunds.csv", ["id", "date", "learner", "email", "path", "status", "requested_kes", "approved_kes", "policy_tier", "payout_reference", "admin_note"],
                         [[r.id, r.created_at.isoformat(), r.user.name, r.user.email, r.path.level, r.status, r.requested_amount, r.approved_amount, r.policy_tier, r.payout_reference, r.admin_note] for r in rows])


@bp.post("/payments/reconcile")
@admin_required
def reconcile_now():
    """Ask Safaricom about every payment still waiting (for when a callback never arrived)."""
    result = billing.reconcile_pending()
    audit(g.user, "payments.reconcile", "", str(result))
    return jsonify(**result)
