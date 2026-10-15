import os


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://lms:lms@localhost:5432/lms"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Google sign-in (OAuth 2.0 / OpenID Connect ID token)
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

    # Session cookie
    COOKIE_SECURE = _bool("COOKIE_SECURE", False)  # set true behind HTTPS
    SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "14"))

    # Local development only: lets you sign in without Google
    DEV_AUTH = _bool("DEV_AUTH", False)

    # Comma separated list of emails that become administrators on first sign-in
    ADMIN_EMAILS = {
        e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()
    }

    # Optional AI coach (Anthropic Messages API). Leave key empty to disable.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    COACH_MODEL = os.environ.get("COACH_MODEL", "claude-sonnet-5-5")

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SEED_DIR = os.path.join(BASE_DIR, "seed_data")
    RESOURCES_DIR = os.environ.get("RESOURCES_DIR", os.path.join(BASE_DIR, "resources"))
    TIMEZONE_OFFSET_HOURS = 3  # East Africa Time, used for streak days
