"""Idempotent loader: paths and lessons from seed_data/*.json."""
import json
import os

from .extensions import db
from .models import Lesson, Path


def _load(seed_dir, name):
    with open(os.path.join(seed_dir, name), encoding="utf-8") as f:
        return json.load(f)


def seed_all(seed_dir):
    paths = _load(seed_dir, "paths.json")
    for item in paths:
        p = Path.query.filter_by(slug=item["slug"]).first() or Path(slug=item["slug"])
        for field in ("level", "title", "tagline", "blurb", "color", "icon", "sort_order", "audience", "outcomes", "tools", "glance", "weeks"):
            setattr(p, field, item[field])
        if p.price_kes is None:  # never overwrite a price the admin has set
            p.price_kes = item.get("price_kes", 0)
        db.session.add(p)
        db.session.flush()
        for les in _load(seed_dir, f"lessons_{item['slug']}.json"):
            row = Lesson.query.filter_by(path_id=p.id, number=les["number"]).first() or Lesson(path_id=p.id, number=les["number"])
            row.week = les["week"]
            row.week_title = les["week_title"]
            row.week_goal = les["week_goal"]
            row.title = les["title"]
            row.content = les["content"]
            db.session.add(row)
    db.session.commit()
    return Path.query.count(), Lesson.query.count()
