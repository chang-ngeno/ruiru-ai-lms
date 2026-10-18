import os


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _database_url() -> str:
    """Accept the URL styles used by Neon / Render / Heroku and make SQLAlchemy happy."""
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://lms:lms@localhost:5432/lms").strip()
    if url.startswith("postgres://"):  # SQLAlchemy 2 no longer understands this alias
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):  # force the psycopg2 driver we install
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

    # ---- Payments (M-Pesa Daraja STK Push) ----
    PAYWALL_ENABLED = _bool("PAYWALL_ENABLED", True)  # false = every lesson open (testing / rollout)
    FREE_PREVIEW_LESSONS = int(os.environ.get("FREE_PREVIEW_LESSONS", "1"))  # lessons open without payment
    MIN_PAYMENT_KES = int(os.environ.get("MIN_PAYMENT_KES", "100"))
    MPESA_ENV = os.environ.get("MPESA_ENV", "sandbox")  # sandbox | production
    MPESA_SIMULATE = _bool("MPESA_SIMULATE", False)  # no Safaricom calls; for local development
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "")  # paybill number or till store number
    MPESA_PARTY_B = os.environ.get("MPESA_PARTY_B", "")  # till number when using Buy Goods (else = shortcode)
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    MPESA_TRANSACTION_TYPE = os.environ.get("MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline")  # or CustomerBuyGoodsOnline
    MPESA_CALLBACK_BASE = os.environ.get("MPESA_CALLBACK_BASE", "")  # public https base, e.g. https://learn.example.com
    MPESA_CALLBACK_SECRET = os.environ.get("MPESA_CALLBACK_SECRET", "")  # random string placed in the callback URL

    # ---- Refunds and workspace ----
    REFUND_ENABLED = _bool("REFUND_ENABLED", True)
    REFUND_PARTIAL_DAYS = int(os.environ.get("REFUND_PARTIAL_DAYS", "3"))  # after starting, refundable this many days from first payment
    REFUND_PARTIAL_PERCENT = int(os.environ.get("REFUND_PARTIAL_PERCENT", "50"))
    WORKSPACE_DAYS = int(os.environ.get("WORKSPACE_DAYS", "30"))  # how long a workspace pass lasts from the first payment
    WORKSPACE_MIN_PERCENT = int(os.environ.get("WORKSPACE_MIN_PERCENT", "25"))  # share of the price needed for workspace access

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SEED_DIR = os.path.join(BASE_DIR, "seed_data")
    RESOURCES_DIR = os.environ.get("RESOURCES_DIR", os.path.join(BASE_DIR, "resources"))
    TIMEZONE_OFFSET_HOURS = 3  # East Africa Time, used for streak days
