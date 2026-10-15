from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, make_response, request

from .extensions import db
from .models import Path, User
from .security import RateLimiter, client_ip, clear_session, login_required, set_session

bp = Blueprint("auth", __name__, url_prefix="/api")
auth_limiter = RateLimiter(limit=20, window_seconds=60)


def _find_path(slug):
    if not slug:
        return None
    return Path.query.filter_by(slug=str(slug)).first()


def _upsert_user(email, name, picture, sub, path):
    """Create a user on first sign-in (with the chosen path) or update an existing one."""
    email = email.lower().strip()
    user = None
    if sub:
        user = User.query.filter_by(google_sub=sub).first()
    if user is None:
        user = User.query.filter_by(email=email).first()
    created = False
    if user is None:
        created = True
        user = User(email=email, google_sub=sub, name=name or email.split("@")[0], picture=picture)
        user.role = "admin" if email in current_app.config["ADMIN_EMAILS"] else "learner"
        if path is not None:
            user.path_id = path.id
        db.session.add(user)
    else:
        if sub and not user.google_sub:
            user.google_sub = sub
        if name:
            user.name = name
        if picture:
            user.picture = picture
        if email in current_app.config["ADMIN_EMAILS"]:
            user.role = "admin"
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return user, created


def _session_response(user, created):
    resp = make_response(jsonify(user=user.to_dict(), created=created))
    return set_session(resp, user)


@bp.post("/auth/google")
def google_sign_in():
    """Verify a Google ID token (from Google Identity Services) and start a session."""
    if not auth_limiter.allow(client_ip()):
        return jsonify(error="Too many attempts. Please wait a minute."), 429
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    if not client_id:
        return jsonify(error="Google sign-in is not configured on the server."), 503
    body = request.get_json(silent=True) or {}
    credential = body.get("credential")
    if not credential:
        return jsonify(error="Missing Google credential."), 400

    try:
        from google.auth.transport import requests as grequests
        from google.oauth2 import id_token

        info = id_token.verify_oauth2_token(credential, grequests.Request(), client_id)
    except Exception:  # invalid signature, wrong audience, expired, network...
        return jsonify(error="Google sign-in could not be verified."), 401

    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return jsonify(error="Invalid token issuer."), 401
    if not info.get("email") or not info.get("email_verified"):
        return jsonify(error="Your Google email address is not verified."), 403

    path = _find_path(body.get("path_slug"))
    user, created = _upsert_user(info["email"], info.get("name"), info.get("picture"), info.get("sub"), path)
    return _session_response(user, created)


@bp.post("/auth/dev-login")
def dev_login():
    """Development only (DEV_AUTH=true): sign in with any email, no Google needed."""
    if not current_app.config["DEV_AUTH"]:
        return jsonify(error="Not found."), 404
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if "@" not in email:
        return jsonify(error="Enter a valid email."), 400
    path = _find_path(body.get("path_slug"))
    user, created = _upsert_user(email, body.get("name") or "", None, None, path)
    return _session_response(user, created)


@bp.post("/auth/logout")
def logout():
    return clear_session(make_response(jsonify(ok=True)))


@bp.get("/me")
@login_required
def me():
    return jsonify(user=g.user.to_dict())


@bp.post("/me/path")
@login_required
def choose_path():
    """Choose a path. Learners can do this once (sign-up); admins can change learners' paths."""
    body = request.get_json(silent=True) or {}
    path = _find_path(body.get("path_slug"))
    if path is None:
        return jsonify(error="Unknown learning path."), 400
    if g.user.path_id is not None and g.user.path_id != path.id:
        return jsonify(error="Your path is already chosen. Ask an administrator to change it."), 409
    g.user.path_id = path.id
    db.session.commit()
    return jsonify(user=g.user.to_dict())
