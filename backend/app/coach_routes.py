"""Optional AI coach that turns the lesson into one practical action."""
import requests
from flask import Blueprint, current_app, g, jsonify, request

from .models import Lesson
from .security import RateLimiter, path_required

bp = Blueprint("coach", __name__, url_prefix="/api")
limiter = RateLimiter(limit=20, window_seconds=300)  # 20 messages / 5 minutes / learner

SYSTEM = """You are the friendly AI Coach for "AI Training for Everyone", a hands-on training programme in Ruiru, Kenya.
The learner is on the {level} path. Today's lesson: "{title}".
Lesson objectives: {objectives}
Today's homework: {homework}

Rules:
- Turn what they learned into ONE specific action they can do today with a phone or laptop.
- Use simple English, short sentences, and examples from everyday life in Kenya where helpful.
- Keep replies under 150 words. Ask at most one question.
- Never ask for or accept passwords, PINs, ID numbers or other private details; remind them not to share these if they try.
- If asked something unrelated to learning or the lesson, politely steer back.
- Be honest: say when you are not sure, and encourage them to verify important facts."""


@bp.get("/coach/status")
@path_required
def status():
    return jsonify(enabled=bool(current_app.config["ANTHROPIC_API_KEY"]))


@bp.post("/coach")
@path_required
def coach():
    key = current_app.config["ANTHROPIC_API_KEY"]
    if not key:
        return jsonify(error="The AI Coach is not switched on yet."), 503
    if not limiter.allow(str(g.user.id)):
        return jsonify(error="You are chatting fast! Please wait a few minutes."), 429

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message or len(message) > 1000:
        return jsonify(error="Write a message of up to 1,000 characters."), 400
    lesson = Lesson.query.filter_by(path_id=g.user.path_id, number=body.get("lesson_number")).first()
    if lesson is None:
        return jsonify(error="Lesson not found."), 404

    history = []
    for m in (body.get("history") or [])[-10:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            history.append({"role": m["role"], "content": m["content"][:2000]})
    # The API needs the conversation to start with a user turn and alternate.
    while history and history[0]["role"] != "user":
        history.pop(0)
    history.append({"role": "user", "content": message})

    c = lesson.content or {}
    system = SYSTEM.format(
        level=g.user.path.level,
        title=lesson.title,
        objectives="; ".join(c.get("objectives", [])),
        homework=c.get("homework", ""),
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": current_app.config["COACH_MODEL"],
                "max_tokens": 500,
                "system": system,
                "messages": history,
            },
            timeout=45,
        )
        r.raise_for_status()
        blocks = r.json().get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    except requests.RequestException:
        return jsonify(error="The coach is unavailable right now. Please try again shortly."), 502
    return jsonify(reply=text or "I could not think of a reply. Please try again.")
