import hashlib
import hmac
import json
import os

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory

from . import billing
from .extensions import db
from .models import Lesson, Path, Progress, utcnow
from .security import login_required, path_required
from .services import compute_summary, get_or_create_progress

bp = Blueprint("learn", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return jsonify(status="ok")


@bp.get("/paths")
def list_paths():
    paths = Path.query.order_by(Path.sort_order).all()
    counts = dict(
        db.session.query(Lesson.path_id, db.func.count(Lesson.id)).group_by(Lesson.path_id).all()
    )
    return jsonify(paths=[p.summary(counts.get(p.id, 0)) for p in paths])


@bp.get("/paths/<slug>")
def path_detail(slug):
    p = Path.query.filter_by(slug=slug).first_or_404()
    return jsonify(path=p.detail())


def _lesson_or_404(number):
    return Lesson.query.filter_by(path_id=g.user.path_id, number=number).first_or_404()


def _locked_response(lesson, state=None):
    """None if the lesson is open, otherwise a 402 response telling the learner what to pay."""
    state = state or billing.billing_state(g.user)
    if billing.lesson_is_open(lesson, state):
        return None
    needed = billing.week_price_needed(lesson.week, state)
    return (
        jsonify(
            error=f"Week {lesson.week} is locked. Pay KES {max(0, needed - state['paid']):,} more to unlock it.",
            code="payment_required",
            week=lesson.week,
            lesson=lesson.number,
            balance=state["balance"],
            to_unlock=max(0, needed - state["paid"]),
        ),
        402,
    )


@bp.get("/lessons")
@path_required
def my_lessons():
    lessons = Lesson.query.filter_by(path_id=g.user.path_id).order_by(Lesson.number).all()
    rows = {r.lesson_id: r for r in Progress.query.filter_by(user_id=g.user.id).all()}
    state = billing.billing_state(g.user)
    out = []
    for l in lessons:
        r = rows.get(l.id)
        out.append(
            {
                "locked": not billing.lesson_is_open(l, state),
                "number": l.number,
                "week": l.week,
                "week_title": l.week_title,
                "week_goal": l.week_goal,
                "title": l.title,
                "completed": bool(r and r.completed_at),
                "quiz_score": r.quiz_score if r else None,
                "quiz_total": r.quiz_total if r else None,
            }
        )
    return jsonify(lessons=out, path=g.user.path.detail(), billing=state)


@bp.get("/lessons/<int:number>")
@path_required
def lesson_detail(number):
    l = _lesson_or_404(number)
    blocked = _locked_response(l)
    if blocked:
        return blocked
    r = Progress.query.filter_by(user_id=g.user.id, lesson_id=l.id).first()
    total = Lesson.query.filter_by(path_id=l.path_id).count()
    return jsonify(
        lesson={
            "number": l.number,
            "week": l.week,
            "week_title": l.week_title,
            "title": l.title,
            "content": l.content,
            "total": total,
        },
        progress={
            "completed": bool(r and r.completed_at),
            "steps_done": (r.steps_done if r else []) or [],
            "notes": (r.notes if r else "") or "",
            "quiz_score": r.quiz_score if r else None,
            "quiz_total": r.quiz_total if r else None,
        },
    )


@bp.put("/lessons/<int:number>/progress")
@path_required
def save_progress(number):
    l = _lesson_or_404(number)
    blocked = _locked_response(l)
    if blocked:
        return blocked
    body = request.get_json(silent=True) or {}
    row = get_or_create_progress(g.user, l)
    if "steps_done" in body:
        steps = body["steps_done"]
        n_steps = len((l.content or {}).get("steps", []))
        if not isinstance(steps, list) or not all(isinstance(i, int) and 0 <= i < n_steps for i in steps):
            return jsonify(error="Invalid steps."), 400
        row.steps_done = sorted(set(steps))
    if "notes" in body:
        notes = body["notes"]
        if not isinstance(notes, str) or len(notes) > 20000:
            return jsonify(error="Notes must be text under 20,000 characters."), 400
        row.notes = notes
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/lessons/<int:number>/complete")
@path_required
def complete(number):
    l = _lesson_or_404(number)
    blocked = _locked_response(l)
    if blocked:
        return blocked
    row = get_or_create_progress(g.user, l)
    if row.completed_at is None:
        row.completed_at = utcnow()
    db.session.commit()
    return jsonify(summary=compute_summary(g.user))


@bp.delete("/lessons/<int:number>/complete")
@path_required
def uncomplete(number):
    l = _lesson_or_404(number)
    blocked = _locked_response(l)
    if blocked:
        return blocked
    row = Progress.query.filter_by(user_id=g.user.id, lesson_id=l.id).first()
    if row:
        row.completed_at = None
        db.session.commit()
    return jsonify(summary=compute_summary(g.user))


@bp.post("/lessons/<int:number>/quiz")
@path_required
def save_quiz(number):
    l = _lesson_or_404(number)
    blocked = _locked_response(l)
    if blocked:
        return blocked
    body = request.get_json(silent=True) or {}
    total = len((l.content or {}).get("quiz", []))
    score = body.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= total:
        return jsonify(error=f"Score must be a whole number from 0 to {total}."), 400
    row = get_or_create_progress(g.user, l)
    row.quiz_score, row.quiz_total = score, total
    db.session.commit()
    return jsonify(quiz_score=score, quiz_total=total)


@bp.get("/progress")
@path_required
def progress_summary():
    return jsonify(summary=compute_summary(g.user))


@bp.get("/glossary")
@path_required
def glossary():
    lessons = Lesson.query.filter_by(path_id=g.user.path_id).order_by(Lesson.number).all()
    state = billing.billing_state(g.user)
    seen, terms = set(), []
    for l in lessons:
        if not billing.lesson_is_open(l, state):
            continue
        for g_item in (l.content or {}).get("glossary", []):
            key = g_item["term"].lower()
            if key in seen:
                continue
            seen.add(key)
            terms.append({**g_item, "lesson": l.number, "lesson_title": l.title})
    terms.sort(key=lambda t: t["term"].lower())
    return jsonify(terms=terms)


def _resource_index():
    with open(os.path.join(current_app.config["SEED_DIR"], "resources.json"), encoding="utf-8") as f:
        return json.load(f)


@bp.get("/resources")
@path_required
def resources():
    if billing.billing_state(g.user)["unlocked_weeks"] < 1:
        return jsonify(error="Resources unlock with your first payment.", code="payment_required"), 402
    items = _resource_index().get(g.user.path.slug, [])
    return jsonify(resources=[{k: v for k, v in i.items() if k != "file"} for i in items])


@bp.get("/resources/<key>")
@path_required
def download_resource(key):
    if billing.billing_state(g.user)["unlocked_weeks"] < 1:
        return jsonify(error="Resources unlock with your first payment.", code="payment_required"), 402
    items = {i["key"]: i for i in _resource_index().get(g.user.path.slug, [])}
    item = items.get(key)
    if not item:
        return jsonify(error="Resource not found."), 404
    return send_from_directory(current_app.config["RESOURCES_DIR"], item["file"], as_attachment=True)


@bp.get("/certificate")
@path_required
def certificate():
    summary = compute_summary(g.user)
    if not summary["finished"]:
        return jsonify(error="Complete every lesson to unlock your certificate."), 403
    code_src = f"{g.user.id}:{g.user.path_id}".encode()
    code = hmac.new(current_app.config["SECRET_KEY"].encode(), code_src, hashlib.sha256).hexdigest()[:10].upper()
    return jsonify(
        name=g.user.name,
        path=g.user.path.summary(),
        completed_at=summary["last_completed_at"],
        hours=summary["hours"],
        code=f"RAI-{code}",
    )
