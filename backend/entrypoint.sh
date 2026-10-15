#!/bin/sh
set -e
# Wait briefly for Postgres, create tables and load the course content (idempotent).
python - << 'PY'
import time, os
from sqlalchemy import create_engine, text
url = os.environ["DATABASE_URL"]
for i in range(30):
    try:
        create_engine(url).connect().execute(text("SELECT 1")); break
    except Exception:
        time.sleep(1)
PY
flask --app wsgi init-db
flask --app wsgi seed
exec gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 3 --timeout 60
