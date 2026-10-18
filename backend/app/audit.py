from .extensions import db
from .models import AuditLog


def audit(admin, action: str, target: str = "", detail: str = ""):
    """Record an admin action. Never lets a logging problem break the action itself."""
    try:
        db.session.add(AuditLog(admin_id=admin.id if admin else None, action=action[:40], target=target[:80], detail=str(detail)[:500]))
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
