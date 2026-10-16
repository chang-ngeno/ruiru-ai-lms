"""Wait until the database accepts connections (Neon may need a few seconds to wake up).

Prints the target host (never the password) so a wrong DATABASE_URL is easy to spot in the logs.
"""
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from .config import Config


def main() -> int:
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    print(f"Connecting to {url.drivername}://{url.host}:{url.port or 5432}/{url.database} as {url.username}", flush=True)
    if url.host in (None, "", "localhost", "127.0.0.1"):
        print("WARNING: DATABASE_URL points at localhost. On Render, set DATABASE_URL to your Neon connection string.", flush=True)
    last = ""
    for attempt in range(1, 41):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.", flush=True)
            return 0
        except Exception as exc:  # noqa: BLE001
            last = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
            print(f"Waiting for database ({attempt}/40): {last}", flush=True)
            time.sleep(3)
    print(f"Could not reach the database: {last}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
  
