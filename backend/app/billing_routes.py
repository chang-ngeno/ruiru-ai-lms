import hmac

from flask import Blueprint, current_app, g, jsonify, request

from . import billing, mpesa
from .extensions import db
from .models import Payment
from .security import RateLimiter, path_required

bp = Blueprint("billing", __name__, url_prefix="/api")
pay_limiter = RateLimiter(limit=6, window_seconds=60)


def _state_payload(user):
    state = billing.billing_state(user)
    payments = Payment.query.filter_by(user_id=user.id, path_id=user.path_id).order_by(Payment.created_at.desc()).limit(30).all()
    return {
        "billing": state,
        "payments": [p.to_dict() for p in payments],
        "mpesa_ready": mpesa.configured(),
        "simulate": bool(current_app.config["MPESA_SIMULATE"]),
        "path": {"level": user.path.level, "title": user.path.title},
        "refund": billing.refund_info(user),
        "workspace": {k: v for k, v in billing.workspace_state(user).items() if k in ("active", "reason", "until")},
    }


@bp.get("/billing")
@path_required
def get_billing():
    return jsonify(_state_payload(g.user))


@bp.post("/billing/discount")
@path_required
def post_discount():
    ok, message = billing.apply_discount_code(g.user, (request.get_json(silent=True) or {}).get("code"))
    if not ok:
        return jsonify(error=message), 400
    return jsonify(message=message, **_state_payload(g.user))


@bp.post("/billing/pay")
@path_required
def pay():
    if not pay_limiter.allow(str(g.user.id)):
        return jsonify(error="Too many attempts. Please wait a minute."), 429
    body = request.get_json(silent=True) or {}
    try:
        payment = billing.create_payment(g.user, body.get("phone"), body.get("amount"))
    except billing.PaymentError as exc:
        extra = {"detail": exc.detail} if exc.detail and g.user.role == "admin" else {}
        return jsonify(error=str(exc), **extra), exc.status
    return jsonify(payment=payment.to_dict(), message="Check your phone and enter your M-Pesa PIN.")


@bp.get("/billing/payments/<int:payment_id>/receipt")
@path_required
def receipt(payment_id):
    p = Payment.query.filter_by(id=payment_id, user_id=g.user.id, status="success").first_or_404()
    state = billing.billing_state(g.user)
    return jsonify(receipt={
        "number": p.mpesa_receipt or f"AIT-{p.id:06d}",
        "date": (p.completed_at or p.created_at).isoformat(),
        "learner": g.user.name, "email": g.user.email,
        "path": f"{p.path.level}: {p.path.title}",
        "amount": p.amount, "method": "M-Pesa" if p.method == "mpesa" else "Recorded by trainer",
        "net_price": state["net"], "paid_to_date": state["paid"], "balance": state["balance"],
    })


@bp.post("/billing/refund")
@path_required
def request_refund():
    body = request.get_json(silent=True) or {}
    try:
        billing.request_refund(g.user, body.get("reason"), body.get("amount"))
    except billing.RefundError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(message="Your request was sent. A trainer will review it.", **_state_payload(g.user))


@bp.post("/billing/refund/<int:refund_id>/cancel")
@path_required
def cancel_refund(refund_id):
    try:
        billing.cancel_refund(g.user, refund_id)
    except billing.RefundError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(**_state_payload(g.user))


@bp.get("/billing/payments/<int:payment_id>")
@path_required
def payment_status(payment_id):
    payment = Payment.query.filter_by(id=payment_id, user_id=g.user.id).first_or_404()
    billing.reconcile(payment)
    return jsonify(payment=payment.to_dict(), billing=billing.billing_state(g.user))


@bp.post("/dev/mpesa/complete/<int:payment_id>")
@path_required
def simulate_complete(payment_id):
    """Only when MPESA_SIMULATE=true: pretend Safaricom answered (for local development)."""
    if not current_app.config["MPESA_SIMULATE"]:
        return jsonify(error="Not found."), 404
    payment = Payment.query.filter_by(id=payment_id, user_id=g.user.id).first_or_404()
    ok = bool((request.get_json(silent=True) or {}).get("success", True))
    billing.apply_result(payment, 0 if ok else 1032, "Simulated", receipt=f"SIM{payment.id:07d}" if ok else None, amount=payment.amount if ok else None)
    return jsonify(payment=payment.to_dict(), billing=billing.billing_state(g.user))


@bp.post("/mpesa/callback/<secret>")
def mpesa_callback(secret):
    """Safaricom calls this (no cookies, no custom headers) when the customer finishes or cancels.

    The random secret in the URL stops strangers from posting fake confirmations; the amount and
    checkout id are also checked against the pending payment before any lesson is unlocked.
    """
    expected = current_app.config["MPESA_CALLBACK_SECRET"]
    if not expected or not hmac.compare_digest(secret, expected):
        return jsonify(error="Not found."), 404
    parsed = mpesa.parse_callback(request.get_json(silent=True))
    if parsed is None:
        current_app.logger.warning("Unreadable M-Pesa callback")
        return jsonify(ResultCode=0, ResultDesc="Accepted")
    try:
        billing.process_callback(parsed)
    except Exception:  # never make Safaricom retry forever because of our bug; the reconcile job will catch up
        db.session.rollback()
        current_app.logger.exception("Error processing M-Pesa callback")
    return jsonify(ResultCode=0, ResultDesc="Accepted")
