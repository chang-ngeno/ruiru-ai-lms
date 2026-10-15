"""Progress, streak and achievement calculations."""
from datetime import timedelta

from flask import current_app

from .extensions import db
from .models import Lesson, Progress, utcnow


def _local_date(dt):
    offset = timedelta(hours=current_app.config["TIMEZONE_OFFSET_HOURS"])
    return (dt + offset).date()


def user_progress_rows(user):
    return Progress.query.filter_by(user_id=user.id).all()


def compute_streak(rows):
    days = {_local_date(r.completed_at) for r in rows if r.completed_at}
    if not days:
        return 0
    today = _local_date(utcnow())
    cursor = today if today in days else today - timedelta(days=1)
    if cursor not in days:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_summary(user):
    lessons = Lesson.query.filter_by(path_id=user.path_id).order_by(Lesson.number).all()
    rows = {r.lesson_id: r for r in user_progress_rows(user)}
    total = len(lessons)
    done = [l for l in lessons if rows.get(l.id) and rows[l.id].completed_at]
    done_numbers = {l.number for l in done}

    weeks = {}
    for l in lessons:
        w = weeks.setdefault(l.week, {"week": l.week, "title": l.week_title, "total": 0, "done": 0})
        w["total"] += 1
        if l.number in done_numbers:
            w["done"] += 1

    next_lesson = next((l for l in lessons if l.number not in done_numbers), None)
    quiz_rows = [r for r in rows.values() if r.quiz_total]
    quiz_avg = (
        round(sum(r.quiz_score / r.quiz_total for r in quiz_rows) / len(quiz_rows) * 100)
        if quiz_rows
        else None
    )
    streak = compute_streak(list(rows.values()))
    percent = round(len(done) / total * 100) if total else 0
    week_list = sorted(weeks.values(), key=lambda w: w["week"])

    good_quizzes = sum(1 for r in quiz_rows if r.quiz_score / r.quiz_total >= 0.8)
    achievements = [
        {"key": "first", "title": "First Step", "desc": "Complete your first lesson", "earned": len(done) >= 1},
        {"key": "streak3", "title": "On Fire", "desc": "Learn 3 days in a row", "earned": streak >= 3},
        {"key": "week", "title": "Week Warrior", "desc": "Finish a full week", "earned": any(w["done"] == w["total"] and w["total"] for w in week_list)},
        {"key": "quiz", "title": "Quiz Whiz", "desc": "Score 80%+ on three self-checks", "earned": good_quizzes >= 3},
        {"key": "half", "title": "Halfway There", "desc": "Complete 50% of the course", "earned": percent >= 50},
        {"key": "grad", "title": "Graduate", "desc": "Complete every lesson", "earned": total > 0 and len(done) == total},
    ]
    last_completed = max((r.completed_at for r in rows.values() if r.completed_at), default=None)
    return {
        "total": total,
        "completed": len(done),
        "percent": percent,
        "streak": streak,
        "hours": len(done) * 3,
        "quiz_average": quiz_avg,
        "weeks": week_list,
        "next_lesson": next_lesson.number if next_lesson else None,
        "next_title": next_lesson.title if next_lesson else None,
        "next_homework": (next_lesson.content or {}).get("homework") if next_lesson else None,
        "achievements": achievements,
        "finished": total > 0 and len(done) == total,
        "last_completed_at": last_completed.isoformat() if last_completed else None,
    }


def get_or_create_progress(user, lesson):
    row = Progress.query.filter_by(user_id=user.id, lesson_id=lesson.id).first()
    if row is None:
        row = Progress(user_id=user.id, lesson_id=lesson.id, steps_done=[], notes="")
        db.session.add(row)
    return row
