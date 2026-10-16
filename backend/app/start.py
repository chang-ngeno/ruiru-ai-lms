"""Container start-up, written in Python so there is no shell script to break.

1. check the environment  2. wait for Postgres (Neon may need to wake)
3. create tables and load the course  4. hand over to gunicorn on Render's $PORT
"""
import os
import sys


def main() -> None:
    print(f"=== Container starting (python {sys.version.split()[0]}) ===", flush=True)
    for name in ("SECRET_KEY", "DATABASE_URL"):
        if not os.environ.get(name):
            print(f"ERROR: {name} is not set. Add it in the service's Environment tab.", file=sys.stderr, flush=True)
            sys.exit(1)

    from .dbwait import main as wait_for_db

    if wait_for_db() != 0:
        print("ERROR: database not reachable, see messages above.", file=sys.stderr, flush=True)
        sys.exit(1)

    from . import create_app
    from .extensions import db
    from .seed import seed_all

    app = create_app()
    with app.app_context():
        db.create_all()
        paths, lessons = seed_all(app.config["SEED_DIR"])
    print(f"Tables ready. Seeded {paths} paths and {lessons} lessons.", flush=True)

    port = os.environ.get("PORT", "5000")
    workers = os.environ.get("WEB_CONCURRENCY", "2")
    print(f"Starting gunicorn on port {port}", flush=True)
    os.execv(
        sys.executable,
        [
            sys.executable, "-m", "gunicorn", "wsgi:app",
            "--bind", f"0.0.0.0:{port}",
            "--workers", workers, "--threads", "2",
            "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-",
        ],
    )


if __name__ == "__main__":
    main()
  
