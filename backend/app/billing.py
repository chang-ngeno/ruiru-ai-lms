"""Billing services: prices, discounts, payments and which lessons a learner may open."""
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy.exc import IntegrityError

from . import billing_rules as rules
from . import mpesa
from .extensions import db
from .models import CheckIn, DiscountCode, Enrollment, Lesson, Payment, Path, Progress, Refund, User, utcnow


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _gross_paid(user_id, path_id) -> int:
    total = (
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter(Payment.user_id == user_id, Payment.path_id == path_id, Payment.status == "success")
        .scalar()
    )
    return int(total or 0)


def _refunded(user_id, path_id) -> int:
    """Money given back: refunds the admin has approved (and later paid out)."""
    total = (
        db.session.query(db.func.coalesce(db.func.sum(Refund.approved_amount), 0))
        .filter(Refund.user_id == user_id, Refund.path_id == path_id, Refund.status.in_(("approved", "paid_out")))
        .scalar()
    )
    return int(total or 0)


def _paid_total(user_id, path_id) -> int:
    """What still counts towards access: payments received minus refunds approved."""
    return max(0, _gross_paid(user_id, path_id) - _refunded(user_id, path_id))


def get_enrollment(user) -> Enrollment:
    """The billing record for the learner's current path (created on first use)."""
    path = user.path
    e = Enrollment.query.filter_by(user_id=user.id, path_id=path.id).first()
    price = path.price_kes or 0
    if e is None:
        e = Enrollment(user_id=user.id, path_id=path.id, price_kes=price, discount_kes=0)
        db.session.add(e)
        db.session.commit()
    elif e.price_kes != price and _gross_paid(user.id, path.id) == 0:
        # Admin changed the price before the learner paid anything: quote the new price.
        e.price_kes = price
        if e.discount_code is not None:
            e.discount_kes = rules.discount_amount(price, e.discount_code.kind, e.discount_code.value)
        e.discount_kes = min(e.discount_kes, price)
        db.session.commit()
    return e


def total_weeks(path_id) -> int:
    return db.session.query(db.func.coalesce(db.func.max(Lesson.week), 0)).filter(Lesson.path_id == path_id).scalar() or 0


def billing_state(user) -> dict:
    cfg = current_app.config
    weeks = total_weeks(user.path_id)
    open_all = (not cfg["PAYWALL_ENABLED"]) or user.role == "admin"
    e = get_enrollment(user)
    net = rules.net_price(e.price_kes, e.discount_kes)
    paid = _paid_total(user.id, user.path_id)
    open_weeks = weeks if open_all else rules.unlocked_weeks(paid, net, weeks)
    return {
        "price": e.price_kes,
        "discount": e.discount_kes,
        "discount_code": e.discount_code.code if e.discount_code else None,
        "discount_note": e.discount_note,
        "net": net,
        "paid": paid,
        "refunded": _refunded(user.id, user.path_id),
        "balance": max(0, net - paid),
        "unlocked_weeks": open_weeks,
        "total_weeks": weeks,
        "fully_paid": net - paid <= 0,
        "open_all": open_all,
        "preview_lessons": cfg["FREE_PREVIEW_LESSONS"],
        "min_payment": cfg["MIN_PAYMENT_KES"],
        "suggestions": [] if open_all else rules.suggested_payments(paid, net, weeks, cfg["MIN_PAYMENT_KES"]),
    }


def lesson_is_open(lesson, state) -> bool:
    if state["open_all"]:
        return True
    return rules.lesson_unlocked(lesson.number, lesson.week, state["unlocked_weeks"], state["preview_lessons"])


def week_price_needed(week, state) -> int:
    return rules.amount_for_week(week, state["net"], state["total_weeks"])


# ----------------------------------------------------------------------------- discounts
def apply_discount_code(user, raw_code: str):
    """Returns (ok, message). One discount per learner per path."""
    code_str = (raw_code or "").strip().upper()
    if not code_str:
        return False, "Enter a discount code."
    code = DiscountCode.query.filter_by(code=code_str).first()
    if code is None or not code.active:
        return False, "That code is not valid."
    now = utcnow()
    if code.valid_from and _aware(code.valid_from) > now:
        return False, "That code is not active yet."
    if code.valid_until and _aware(code.valid_until) < now:
        return False, "That code has expired."
    if code.path_id and code.path_id != user.path_id:
        return False, "That code is for a different path."
    if code.user_email and code.user_email.lower() != user.email.lower():
        return False, "That code was issued to someone else."
    e = get_enrollment(user)
    if e.discount_kes > 0 or e.discount_code_id:
        return False, "A discount is already applied to your account."
    if code.max_redemptions is not None:
        used = Enrollment.query.filter_by(discount_code_id=code.id).count()
        if used >= code.max_redemptions:
            return False, "That code has been used up."
    e.discount_code_id = code.id
    e.discount_kes = rules.discount_amount(e.price_kes, code.kind, code.value)
    e.discount_note = code.description or code.code
    db.session.commit()
    return True, "Discount applied."


# ----------------------------------------------------------------------------- payments
class PaymentError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def create_payment(user, phone_raw, amount_raw) -> Payment:
    cfg = current_app.config
    state = billing_state(user)
    if state["open_all"] and not cfg["PAYWALL_ENABLED"]:
        raise PaymentError("Payments are switched off right now.")
    if state["balance"] <= 0:
        raise PaymentError("You have already paid in full.")
    phone = rules.normalize_phone(phone_raw)
    if phone is None:
        raise PaymentError("Enter a valid Safaricom number, for example 0712 345 678.")
    if isinstance(amount_raw, bool) or not isinstance(amount_raw, (int, float, str)):
        raise PaymentError("Enter a whole amount in KES.")
    try:
        amount = int(float(amount_raw))
        if float(amount_raw) != amount:
            raise ValueError
    except (TypeError, ValueError):
        raise PaymentError("Enter a whole amount in KES.")
    minimum = min(cfg["MIN_PAYMENT_KES"], state["balance"])
    if amount < minimum:
        raise PaymentError(f"The smallest payment is KES {minimum:,}.")
    if amount > state["balance"]:
        raise PaymentError(f"You only owe KES {state['balance']:,}. Choose a smaller amount.")
    if not mpesa.configured():
        raise PaymentError("M-Pesa payments are not switched on yet. Please contact your trainer.", 503)

    recent = utcnow() - timedelta(seconds=90)
    for p in Payment.query.filter_by(user_id=user.id, status="pending").all():
        if _aware(p.created_at) > recent:
            raise PaymentError("A payment request is already waiting on your phone. Finish it or wait a minute.", 409)

    payment = Payment(user_id=user.id, path_id=user.path_id, amount=amount, phone=phone, method="mpesa", status="initiated")
    db.session.add(payment)
    db.session.commit()
    try:
        res = mpesa.stk_push(phone, amount, f"AIT{user.id}", "AI Training")
    except mpesa.MpesaError as exc:
        payment.status, payment.result_desc, payment.completed_at = "failed", str(exc)[:300], utcnow()
        db.session.commit()
        raise PaymentError(str(exc), 502)
    payment.merchant_request_id = res["merchant_request_id"]
    payment.checkout_request_id = res["checkout_request_id"]
    payment.status = "pending"
    db.session.commit()
    return payment


def _finish(payment, status, code=None, desc=None):
    payment.status = status
    payment.result_code = None if code is None else str(code)
    payment.result_desc = (desc or "")[:300]
    payment.completed_at = utcnow()


def apply_result(payment, result_code, desc, receipt=None, amount=None, phone=None, from_query=False):
    """Apply a Safaricom outcome to a payment. Safe to call more than once (idempotent)."""
    if payment.status == "success":
        if receipt and not payment.mpesa_receipt:
            payment.mpesa_receipt = receipt
            db.session.commit()
        return payment
    if payment.status in ("failed", "expired", "review") and not (str(result_code) == "0" and payment.status == "expired"):
        return payment
    if str(result_code) != "0":
        _finish(payment, "failed", result_code, desc)
        db.session.commit()
        return payment
    # Success reported. A callback tells us the amount paid: it must match what we asked for.
    if amount is not None and int(round(amount)) != payment.amount:
        current_app.logger.error("Payment %s amount mismatch: expected %s got %s", payment.id, payment.amount, amount)
        _finish(payment, "review", result_code, f"Amount mismatch: expected {payment.amount}, received {amount}")
        db.session.commit()
        return payment
    payment.mpesa_receipt = receipt or payment.mpesa_receipt
    _finish(payment, "success", result_code, desc or "Paid")
    try:
        db.session.commit()
    except IntegrityError:  # the same receipt was processed by another request
        db.session.rollback()
    return payment


def process_callback(parsed: dict):
    payment = Payment.query.filter_by(checkout_request_id=parsed["checkout_request_id"]).with_for_update().first()
    if payment is None:
        current_app.logger.warning("Callback for unknown checkout id %s", parsed["checkout_request_id"])
        return None
    return apply_result(payment, parsed["result_code"], parsed["result_desc"], parsed["receipt"], parsed["amount"], parsed["phone"])


def reconcile(payment):
    """If the callback is late or lost, ask Safaricom. Called while the learner's page polls."""
    if payment.status != "pending" or not payment.checkout_request_id or current_app.config["MPESA_SIMULATE"]:
        return payment
    now = utcnow()
    age = (now - _aware(payment.created_at)).total_seconds()
    if age > 15 * 60:
        _finish(payment, "expired", None, "No response from M-Pesa")
        db.session.commit()
        return payment
    if age < 30 or (payment.last_query_at and (now - _aware(payment.last_query_at)).total_seconds() < 10):
        return payment
    payment.last_query_at = now
    db.session.commit()
    try:
        q = mpesa.stk_query(payment.checkout_request_id)
    except mpesa.MpesaError:
        return payment
    if q["state"] == "success":
        apply_result(payment, 0, q["desc"] or "Paid", from_query=True)
    elif q["state"] == "failed":
        apply_result(payment, q["code"], q["desc"], from_query=True)
    return payment


def record_manual(admin, user, amount: int, method_note: str) -> Payment:
    if not user.path_id:
        raise PaymentError("That learner has not chosen a path yet.")
    p = Payment(user_id=user.id, path_id=user.path_id, amount=int(amount), method="manual", status="success",
                note=(method_note or "Manual payment")[:300], recorded_by=admin.id, completed_at=utcnow())
    db.session.add(p)
    db.session.commit()
    return p


# ----------------------------------------------------------------------------- refunds
class RefundError(Exception):
    pass


def _first_payment_time(user_id, path_id):
    return (
        db.session.query(db.func.min(Payment.completed_at))
        .filter(Payment.user_id == user_id, Payment.path_id == path_id, Payment.status == "success")
        .scalar()
    )


def learner_started(user) -> bool:
    """Has the learner done anything in a paid lesson (beyond the free preview)?"""
    preview = current_app.config["FREE_PREVIEW_LESSONS"]
    return (
        db.session.query(Progress.id)
        .join(Lesson, Lesson.id == Progress.lesson_id)
        .filter(Progress.user_id == user.id, Lesson.path_id == user.path_id, Lesson.number > preview)
        .first()
        is not None
    )


def refund_suggestion(user) -> dict:
    cfg = current_app.config
    refundable = _paid_total(user.id, user.path_id)
    first = _aware(_first_payment_time(user.id, user.path_id))
    days = (utcnow() - first).total_seconds() / 86400 if first else 0
    tier, eligible = rules.refund_policy(learner_started(user), days, refundable, cfg["REFUND_PARTIAL_DAYS"], cfg["REFUND_PARTIAL_PERCENT"])
    return {"refundable": refundable, "tier": tier, "eligible": eligible}


def refund_info(user) -> dict:
    cfg = current_app.config
    s = refund_suggestion(user)
    rows = Refund.query.filter_by(user_id=user.id, path_id=user.path_id).order_by(Refund.created_at.desc()).all()
    open_req = next((r for r in rows if r.status == "requested"), None)
    return {
        "enabled": cfg["REFUND_ENABLED"],
        "can_request": bool(cfg["REFUND_ENABLED"] and s["refundable"] > 0 and open_req is None and user.role != "admin"),
        "refundable": s["refundable"],
        "tier": s["tier"],
        "eligible": s["eligible"],
        "partial_days": cfg["REFUND_PARTIAL_DAYS"],
        "partial_percent": cfg["REFUND_PARTIAL_PERCENT"],
        "open": open_req.to_dict() if open_req else None,
        "history": [r.to_dict() for r in rows],
    }


def request_refund(user, reason: str, amount_raw=None) -> Refund:
    if not current_app.config["REFUND_ENABLED"]:
        raise RefundError("Refund requests are switched off.")
    info = refund_info(user)
    if info["open"]:
        raise RefundError("You already have a refund request waiting for approval.")
    if info["refundable"] <= 0:
        raise RefundError("You have nothing to refund.")
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise RefundError("Please tell us briefly why you are asking for a refund.")
    amount = info["eligible"] if info["eligible"] > 0 else info["refundable"]
    if amount_raw not in (None, ""):
        try:
            amount = int(float(amount_raw))
            if float(amount_raw) != amount:
                raise ValueError
        except (TypeError, ValueError):
            raise RefundError("Enter a whole amount in KES.")
    if amount < 1 or amount > info["refundable"]:
        raise RefundError(f"Choose an amount between KES 1 and KES {info['refundable']:,}.")
    r = Refund(user_id=user.id, path_id=user.path_id, reason=reason[:500], requested_amount=amount,
               policy_tier=info["tier"], eligible_amount=info["eligible"], status="requested")
    db.session.add(r)
    db.session.commit()
    return r


def cancel_refund(user, refund_id) -> Refund:
    r = Refund.query.filter_by(id=refund_id, user_id=user.id).first()
    if r is None or r.status != "requested":
        raise RefundError("That request cannot be cancelled.")
    r.status = "cancelled"
    r.decided_at = utcnow()
    db.session.commit()
    return r


def approve_refund(admin, refund: Refund, amount: int, note: str = "") -> Refund:
    if refund.status != "requested":
        raise RefundError("Only waiting requests can be approved.")
    refundable = max(0, _gross_paid(refund.user_id, refund.path_id) - _refunded(refund.user_id, refund.path_id))
    if amount < 1 or amount > refundable:
        raise RefundError(f"Amount must be between KES 1 and KES {refundable:,} (what this learner has paid and not had back).")
    refund.status, refund.approved_amount = "approved", int(amount)
    refund.admin_note, refund.decided_by, refund.decided_at = (note or "")[:500], admin.id, utcnow()
    db.session.commit()
    return refund


def reject_refund(admin, refund: Refund, note: str) -> Refund:
    if refund.status != "requested":
        raise RefundError("Only waiting requests can be rejected.")
    if not (note or "").strip():
        raise RefundError("Please give a short reason so the learner understands.")
    refund.status, refund.admin_note = "rejected", note.strip()[:500]
    refund.decided_by, refund.decided_at = admin.id, utcnow()
    db.session.commit()
    return refund


def mark_refund_paid(admin, refund: Refund, method: str, reference: str) -> Refund:
    if refund.status != "approved":
        raise RefundError("Only approved refunds can be marked as paid out.")
    if not (reference or "").strip():
        raise RefundError("Enter the M-Pesa or bank reference of the payout.")
    refund.status = "paid_out"
    refund.payout_method, refund.payout_reference, refund.paid_out_at = (method or "M-Pesa")[:40], reference.strip()[:80], utcnow()
    db.session.commit()
    return refund


def admin_create_refund(admin, user, amount: int, reason: str) -> Refund:
    """Admin starts (and approves) a refund on a learner's behalf, for example after a phone call."""
    if not user.path_id:
        raise RefundError("That learner has not chosen a path.")
    s = refund_suggestion(user)
    r = Refund(user_id=user.id, path_id=user.path_id, reason=(reason or "Requested by phone")[:500], requested_amount=int(amount),
               policy_tier=s["tier"], eligible_amount=s["eligible"], status="requested")
    db.session.add(r)
    db.session.flush()
    try:
        approve_refund(admin, r, int(amount), "Started by admin")
    except RefundError:
        db.session.rollback()
        raise
    return r


# ----------------------------------------------------------------------------- workspace pass
def workspace_state(user) -> dict:
    """Is the learner allowed into the physical workspace? Tied to payment (and the pass period)."""
    cfg = current_app.config
    code = rules.workspace_code(user.id, cfg["SECRET_KEY"])
    base = {"code": code, "days": cfg["WORKSPACE_DAYS"], "min_percent": cfg["WORKSPACE_MIN_PERCENT"], "until": None, "required": 0, "paid": 0}
    if user.role == "admin" or not cfg["PAYWALL_ENABLED"]:
        return {**base, "active": True, "reason": "Open to everyone right now."}
    if not user.path_id:
        return {**base, "active": False, "reason": "Choose a path first."}
    e = get_enrollment(user)
    net = rules.net_price(e.price_kes, e.discount_kes)
    paid = _paid_total(user.id, user.path_id)
    required = 0 if net <= 0 else max(1, -(-net * cfg["WORKSPACE_MIN_PERCENT"] // 100))
    base.update(required=required, paid=paid)
    if net > 0 and paid < required:
        need = required - paid
        return {**base, "active": False, "reason": f"Pay KES {need:,} more to unlock the workspace."}
    start = _aware(_first_payment_time(user.id, user.path_id)) if net > 0 else _aware(e.created_at)
    if start is None:
        return {**base, "active": False, "reason": "Make a payment to unlock the workspace."}
    until = _aware(e.workspace_until) or (start + timedelta(days=cfg["WORKSPACE_DAYS"]))
    base["until"] = until.isoformat()
    if until < utcnow():
        return {**base, "active": False, "reason": "Your workspace pass has ended. Ask your trainer about extending it."}
    return {**base, "active": True, "reason": "Active"}


def verify_workspace(admin, raw_code: str) -> dict:
    """Front-desk check: decode the pass, decide, and log the scan."""
    user_id = rules.decode_workspace_code(raw_code, current_app.config["SECRET_KEY"])
    user = db.session.get(User, user_id) if user_id else None
    if user is None:
        return {"valid": False, "allowed": False, "reason": "This code is not a valid workspace pass."}
    state = workspace_state(user)
    db.session.add(CheckIn(user_id=user.id, checked_by=admin.id, allowed=state["active"], reason=state["reason"][:200]))
    db.session.commit()
    return {
        "valid": True, "allowed": state["active"], "reason": state["reason"], "until": state["until"],
        "learner": {"id": user.id, "name": user.name, "email": user.email, "picture": user.picture,
                    "path": user.path.level if user.path else None},
    }


# ----------------------------------------------------------------------------- housekeeping
def reconcile_pending(limit: int = 50) -> dict:
    """Ask Safaricom about payments still pending (callbacks can be lost). Safe to run often."""
    rows = Payment.query.filter(Payment.status.in_(("pending", "initiated")), Payment.checkout_request_id.isnot(None)).order_by(Payment.created_at).limit(limit).all()
    before = {p.id: p.status for p in rows}
    for p in rows:
        reconcile(p)
    changed = sum(1 for p in rows if p.status != before[p.id])
    return {"checked": len(rows), "updated": changed}


def export_user_data(user) -> dict:
    """Everything we hold about a learner (Kenya Data Protection Act: right of access)."""
    lessons = {l.id: l for l in Lesson.query.filter_by(path_id=user.path_id).all()} if user.path_id else {}
    progress = Progress.query.filter_by(user_id=user.id).all()
    e = Enrollment.query.filter_by(user_id=user.id).all()
    return {
        "profile": {"name": user.name, "email": user.email, "role": user.role, "joined": user.created_at.isoformat() if user.created_at else None,
                    "path": user.path.title if user.path else None},
        "progress": [{"lesson": lessons[p.lesson_id].number if p.lesson_id in lessons else p.lesson_id, "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                      "quiz": f"{p.quiz_score}/{p.quiz_total}" if p.quiz_total else None, "notes": p.notes} for p in progress],
        "billing": [{"price": x.price_kes, "discount": x.discount_kes, "note": x.discount_note} for x in e],
        "payments": [p.to_dict() for p in Payment.query.filter_by(user_id=user.id).order_by(Payment.created_at).all()],
        "refunds": [r.to_dict() for r in Refund.query.filter_by(user_id=user.id).order_by(Refund.created_at).all()],
        "workspace_scans": [{"at": c.created_at.isoformat(), "allowed": c.allowed} for c in CheckIn.query.filter_by(user_id=user.id).all()],
    }


def delete_user_data(user):
    """Erase personal data but keep the financial records we must retain (amounts, receipts, dates)."""
    Progress.query.filter_by(user_id=user.id).delete()
    CheckIn.query.filter_by(user_id=user.id).delete()
    for p in Payment.query.filter_by(user_id=user.id).all():
        p.phone = None
    for r in Refund.query.filter_by(user_id=user.id).all():
        r.reason = "[removed at the learner's request]"
    user.name = "Deleted learner"
    user.email = f"deleted-{user.id}@deleted.invalid"
    user.google_sub = None
    user.picture = None
    db.session.commit()
