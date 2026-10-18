from flask import Blueprint, g, jsonify, request

from .extensions import db
from . import billing_rules as rules
from .models import Enrollment, Lesson, Path, Payment, Progress, Refund, User
from .audit import audit
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
    collected = db.session.query(Payment.path_id, db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(Payment.status == "success").group_by(Payment.path_id).all()
    refunded = dict(db.session.query(Refund.path_id, db.func.coalesce(db.func.sum(Refund.approved_amount), 0)).filter(Refund.status.in_(("approved", "paid_out"))).group_by(Refund.path_id).all())
    revenue = {pid: int(total) - int(refunded.get(pid, 0)) for pid, total in collected}  # net of refunds
    refunds_waiting = Refund.query.filter_by(status="requested").count()
    payouts_due = Refund.query.filter_by(status="approved").count()
    pending = Payment.query.filter(Payment.status.in_(("pending", "initiated"))).count()
    review = Payment.query.filter_by(status="review").count()
    return jsonify(
        revenue_total=sum(revenue.values()),
        pending_payments=pending,
        review_payments=review,
        refunds_waiting=refunds_waiting,
        payouts_due=payouts_due,
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
                "price_kes": p.price_kes or 0,
                "revenue": revenue.get(p.id, 0),
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
    paid = {}
    enrol = {}
    if ids:
        for uid, pid, total in db.session.query(Payment.user_id, Payment.path_id, db.func.sum(Payment.amount)).filter(Payment.user_id.in_(ids), Payment.status == "success").group_by(Payment.user_id, Payment.path_id).all():
            paid[(uid, pid)] = int(total)
        for e in Enrollment.query.filter(Enrollment.user_id.in_(ids)).all():
            enrol[(e.user_id, e.path_id)] = e
    for uid, pid, total in db.session.query(Refund.user_id, Refund.path_id, db.func.sum(Refund.approved_amount)).filter(Refund.user_id.in_(ids), Refund.status.in_(("approved", "paid_out"))).group_by(Refund.user_id, Refund.path_id).all():
        paid[(uid, pid)] = max(0, paid.get((uid, pid), 0) - int(total or 0))
    prices = {p.id: (p.price_kes or 0) for p in Path.query.all()}

    def money(u):
        e = enrol.get((u.id, u.path_id))
        price = e.price_kes if e else prices.get(u.path_id, 0)
        disc = e.discount_kes if e else 0
        net = rules.net_price(price, disc)
        return {"price": price, "discount": disc, "net": net, "paid": paid.get((u.id, u.path_id), 0)}

    return jsonify(
        learners=[
            {
                **money(u),
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
    old = user.path.slug if user.path else None
    user.path_id = path.id
    db.session.commit()
    audit(g.user, "learner.path", f"user:{user.id}", f"{old} -> {path.slug}")
    return jsonify(ok=True)
