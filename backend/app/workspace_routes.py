from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request

from . import billing
from .extensions import db
from .audit import audit
from .models import CheckIn, User, utcnow
from .security import admin_required, path_required

bp = Blueprint("workspace", __name__, url_prefix="/api")


@bp.get("/workspace")
@path_required
def my_pass():
    """The learner's workspace pass: active only while payments cover it."""
    return jsonify(workspace=billing.workspace_state(g.user))


@bp.post("/admin/workspace/verify")
@admin_required
def verify():
    """Front desk: check a pass code (typed, or from the QR link) and log the scan."""
    code = (request.get_json(silent=True) or {}).get("code") or ""
    return jsonify(billing.verify_workspace(g.user, code))


@bp.get("/admin/workspace/checkins")
@admin_required
def checkins():
    since = utcnow() - timedelta(days=1)
    rows = CheckIn.query.filter(CheckIn.created_at >= since).order_by(CheckIn.created_at.desc()).limit(100).all()
    return jsonify(checkins=[{"id": c.id, "learner": c.user.name, "email": c.user.email, "allowed": c.allowed, "reason": c.reason, "at": c.created_at.isoformat()} for c in rows])


@bp.post("/admin/learners/<int:user_id>/workspace")
@admin_required
def set_until(user_id):
    """Extend (or shorten) one learner's workspace pass. Send until=null to go back to the normal period."""
    user = db.session.get(User, user_id)
    if user is None or not user.path_id:
        return jsonify(error="Learner not found or has no path."), 404
    raw = (request.get_json(silent=True) or {}).get("until")
    e = billing.get_enrollment(user)
    if raw in (None, ""):
        e.workspace_until = None
    else:
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return jsonify(error="Date must look like 2026-12-31."), 400
        e.workspace_until = (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).replace(hour=23, minute=59, second=59) if len(str(raw)) <= 10 else dt
    db.session.commit()
    audit(g.user, "workspace.until", f"user:{user.id}", str(raw))
    return jsonify(workspace=billing.workspace_state(user))
