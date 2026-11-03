"""Health endpoints.

  GET /health, /healthz  liveness: the process is up. No database, so it never fails while Neon wakes. Use for Render's health check.
  GET /api/health        readiness: also checks the database (503 if it is down). Use for uptime monitors; works through the website too.
  GET /                  tiny service banner for hosts that probe the root.
"""
import os
import time
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify

from .extensions import db

bp = Blueprint("health", __name__)
STARTED = time.time()


def _info() -> dict:
    return {
        "service": "sequa-launchpad-api",
        "time": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - STARTED),
        "commit": (os.environ.get("RENDER_GIT_COMMIT") or os.environ.get("GIT_COMMIT") or "")[:7] or None,
    }


def _no_store(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.get("/health")
@bp.get("/healthz")
def liveness():
    return _no_store(jsonify(status="ok", **_info()))


@bp.get("/")
def root():
    return _no_store(jsonify(status="ok", service="sequa-launchpad-api", health="/health", readiness="/api/health"))


@bp.get("/api/health")
def readiness():
    try:
        db.session.execute(db.text("SELECT 1"))
        up = True
    except Exception:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("Health check: database is not reachable")
        up = False
    body = {"status": "ok" if up else "degraded", "database": "up" if up else "down", **_info()}
    return _no_store(jsonify(body)), (200 if up else 503)
  
