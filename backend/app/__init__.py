import logging

import click
from flask import Flask, jsonify, request

from .config import Config
from .extensions import db


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    if not app.config["SECRET_KEY"]:
        if app.config["DEV_AUTH"] or app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "dev-only-secret-not-for-production"
        else:
            raise RuntimeError("SECRET_KEY is not set. Generate one: python -c \"import secrets; print(secrets.token_hex(32))\"")

    # Serverless Postgres (Neon) closes idle connections and limits total connections:
    # keep pools small, test connections before use and recycle them often.
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql") and "SQLALCHEMY_ENGINE_OPTIONS" not in (overrides or {}):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 240,
            "pool_size": 3,
            "max_overflow": 2,
        }

    logging.basicConfig(level=logging.INFO)
    db.init_app(app)

    from . import admin_billing_routes, admin_routes, auth_routes, billing_routes, coach_routes, learn_routes, privacy_routes, workspace_routes

    for module in (auth_routes, learn_routes, admin_routes, admin_billing_routes, billing_routes, workspace_routes, privacy_routes, coach_routes):
        app.register_blueprint(module.bp)

    @app.before_request
    def csrf_guard():
        # The session cookie is SameSite=Lax; also require a custom header on writes,
        # which a cross-site form or image request cannot send.
        if request.path.startswith("/api/mpesa/callback/"):
            return None  # called by Safaricom; protected by the secret in the URL instead
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path.startswith("/api/"):
            if request.headers.get("X-Requested-With") != "XMLHttpRequest":
                return jsonify(error="Missing request header."), 403

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Not found."), 404

    @app.errorhandler(500)
    def server_error(_):
        return jsonify(error="Something went wrong on our side."), 500

    @app.cli.command("init-db")
    def init_db():
        """Create tables."""
        from . import migrate

        db.create_all()
        migrate.run(db)
        click.echo("Tables created.")

    @app.cli.command("reconcile-payments")
    def reconcile_payments():
        """Ask Safaricom about payments still pending. Run every few minutes from a cron job."""
        from . import billing

        click.echo(str(billing.reconcile_pending()))

    @app.cli.command("seed")
    def seed():
        """Load paths and lessons (safe to run repeatedly)."""
        from .seed import seed_all

        paths, lessons = seed_all(app.config["SEED_DIR"])
        click.echo(f"Seeded {paths} paths and {lessons} lessons.")

    return app
