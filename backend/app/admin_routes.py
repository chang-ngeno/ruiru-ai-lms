from flask import Blueprint, jsonify, request

from .extensions import db
from .models import Lesson, Path, Progress, User
from .security import admin_required
from .auth_routes import _find_path

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/overview")
@admin_required
def overview():
    paths = Path.query.order_by(Path.sort_order).all()
    lesson_counts = dict(
        db.session.query(Lesson.path_id, db.func.count(Lesson.id)).group_by(Lesson.path_id).all()
    )
    learners_by_path = dict(
        db.session.query(User.path_id, db.func.count(User.id))
        .filter(User.role == "learner")
        .group_by(User.path_id)
        .all()
    )
    completions = dict(
        db.session.query(Lesson.path_id, db.func.count(Progress.id))
        .join(Progress, Progress.lesson_id == Lesson.id)
        .filter(Progress.completed_at.isnot(None))
        .group_by(Lesson.path_id)
        .all()
    )
    return jsonify(
        learners=User.query.filter_by(role="learner").count(),
        unassigned=User.query.filter(User.role == "learner", User.path_id.is_(None)).count(),
        paths=[
            {
                "slug": p.slug,
                "level": p.level,
                "color": p.color,
                "learners": learners_by_path.get(p.id, 0),
                "lessons": lesson_counts.get(p.id, 0),
                "completions": completions.get(p.id, 0),
            }
            for p in paths
        ],
    )


@bp.get("/learners")
@admin_required
def learners():
    q = (request.args.get("q") or "").strip().lower()
    slug = request.args.get("path")
    query = User.query.filter(User.role == "learner")
    if slug:
        p = _find_path(slug)
        query = query.filter(User.path_id == (p.id if p else -1))
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(db.func.lower(User.email).like(like), db.func.lower(User.name).like(like)))
    users = query.order_by(User.created_at.desc()).limit(500).all()
    ids = [u.id for u in users]
    done = {}
    last = {}
    if ids:
        for uid, n, latest in (
            db.session.query(Progress.user_id, db.func.count(Progress.id), db.func.max(Progress.completed_at))
            .filter(Progress.user_id.in_(ids), Progress.completed_at.isnot(None))
            .group_by(Progress.user_id)
            .all()
        ):
            done[uid], last[uid] = n, latest
    totals = dict(
        db.session.query(Lesson.path_id, db.func.count(Lesson.id)).group_by(Lesson.path_id).all()
    )
    return jsonify(
        learners=[
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "path": u.path.slug if u.path else None,
                "path_level": u.path.level if u.path else None,
                "completed": done.get(u.id, 0),
                "total": totals.get(u.path_id, 0),
                "last_active": (last.get(u.id) or u.last_login_at).isoformat() if (last.get(u.id) or u.last_login_at) else None,
                "joined": u.created_at.isoformat(),
            }
            for u in users
        ]
    )


@bp.patch("/learners/<int:user_id>/path")
@admin_required
def change_path(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify(error="Learner not found."), 404
    path = _find_path((request.get_json(silent=True) or {}).get("path_slug"))
    if path is None:
        return jsonify(error="Unknown learning path."), 400
    user.path_id = path.id
    db.session.commit()
    return jsonify(ok=True)
