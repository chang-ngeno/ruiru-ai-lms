"""Tiny schema upgrades for databases created by an earlier version (create_all never alters tables)."""
from sqlalchemy import inspect, text


def run(db):
    engine = db.engine
    insp = inspect(engine)
    tables = insp.get_table_names()
    if "enrollments" in tables:
        ecols = {c["name"] for c in insp.get_columns("enrollments")}
        if "workspace_until" not in ecols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE enrollments ADD COLUMN workspace_until TIMESTAMP"))
    if "paths" in tables:
        cols = {c["name"] for c in insp.get_columns("paths")}
        if "price_kes" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE paths ADD COLUMN price_kes INTEGER"))
