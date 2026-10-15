from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Path(db.Model):
    __tablename__ = "paths"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    level = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    tagline = db.Column(db.Text, nullable=False, default="")
    blurb = db.Column(db.Text, nullable=False, default="")
    color = db.Column(db.String(12), nullable=False, default="#0B2A6F")
    icon = db.Column(db.String(24), nullable=False, default="bulb")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    audience = db.Column(db.Text, nullable=False, default="")
    outcomes = db.Column(db.JSON, nullable=False, default=list)
    tools = db.Column(db.JSON, nullable=False, default=list)
    glance = db.Column(db.JSON, nullable=False, default=list)
    weeks = db.Column(db.JSON, nullable=False, default=list)

    lessons = db.relationship("Lesson", backref="path", order_by="Lesson.number", lazy="dynamic")

    def summary(self, lesson_count=None):
        return {
            "slug": self.slug,
            "level": self.level,
            "title": self.title,
            "tagline": self.tagline,
            "blurb": self.blurb,
            "color": self.color,
            "icon": self.icon,
            "lessons": lesson_count if lesson_count is not None else self.lessons.count(),
        }

    def detail(self):
        d = self.summary()
        d.update(
            audience=self.audience,
            outcomes=self.outcomes,
            tools=self.tools,
            glance=self.glance,
            weeks=self.weeks,
        )
        return d


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_sub = db.Column(db.String(64), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False, default="")
    picture = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="learner")  # learner | admin
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    path = db.relationship("Path")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "role": self.role,
            "path": self.path.summary() if self.path else None,
        }


class Lesson(db.Model):
    __tablename__ = "lessons"
    __table_args__ = (db.UniqueConstraint("path_id", "number", name="uq_lesson_path_number"),)

    id = db.Column(db.Integer, primary_key=True)
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    week_title = db.Column(db.String(160), nullable=False)
    week_goal = db.Column(db.Text, nullable=False, default="")
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.JSON, nullable=False, default=dict)


class Progress(db.Model):
    __tablename__ = "progress"
    __table_args__ = (db.UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    steps_done = db.Column(db.JSON, nullable=False, default=list)
    notes = db.Column(db.Text, nullable=False, default="")
    quiz_score = db.Column(db.Integer, nullable=True)
    quiz_total = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    lesson = db.relationship("Lesson")
