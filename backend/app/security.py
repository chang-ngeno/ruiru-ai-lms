import functools
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, g, jsonify, request

from .extensions import db
from .models import User

COOKIE_NAME = "rl_session"


def issue_token(user: User) -> str:
    days = current_app.config["SESSION_DAYS"]
    payload = {
        "sub": str(user.id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=days),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def set_session(response, user: User):
    response.set_cookie(
        COOKIE_NAME,
        issue_token(user),
        max_age=current_app.config["SESSION_DAYS"] * 86400,
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite="Lax",
        path="/",
    )
    return response


def clear_session(response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


def load_user():
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return db.session.get(User, int(data["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        return None


def login_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        user = load_user()
        if user is None:
            return jsonify(error="Please sign in."), 401
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def path_required(fn):
    """Signed in AND has chosen a learning path."""

    @functools.wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user.path_id is None:
            return jsonify(error="Please choose a learning path first.", code="no_path"), 409
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @functools.wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user.role != "admin":
            return jsonify(error="Administrators only."), 403
        return fn(*args, **kwargs)

    return wrapper


class RateLimiter:
    """Small in-memory sliding-window limiter. Use Redis if you run several workers."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.hits = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr) or "unknown"
