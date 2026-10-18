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
    price_kes = db.Column(db.Integer, nullable=True)  # None until seeded; admin can edit; 0 = free

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
            "price_kes": self.price_kes or 0,
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


class DiscountCode(db.Model):
    __tablename__ = "discount_codes"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=False, default="")
    kind = db.Column(db.String(10), nullable=False)  # percent | fixed
    value = db.Column(db.Integer, nullable=False)  # percent (1-100) or KES
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=True)  # None = any path
    user_email = db.Column(db.String(255), nullable=True)  # None = anyone; otherwise only this learner
    max_redemptions = db.Column(db.Integer, nullable=True)
    valid_from = db.Column(db.DateTime(timezone=True), nullable=True)
    valid_until = db.Column(db.DateTime(timezone=True), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    path = db.relationship("Path")


class Enrollment(db.Model):
    """A learner's billing record for one path: the price they were quoted and any discount."""

    __tablename__ = "enrollments"
    __table_args__ = (db.UniqueConstraint("user_id", "path_id", name="uq_enrollment_user_path"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False)
    price_kes = db.Column(db.Integer, nullable=False)
    discount_kes = db.Column(db.Integer, nullable=False, default=0)
    discount_code_id = db.Column(db.Integer, db.ForeignKey("discount_codes.id"), nullable=True)
    discount_note = db.Column(db.String(300), nullable=False, default="")
    workspace_until = db.Column(db.DateTime(timezone=True), nullable=True)  # admin override of the pass end date
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    discount_code = db.relationship("DiscountCode")


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    method = db.Column(db.String(12), nullable=False, default="mpesa")  # mpesa | manual
    status = db.Column(db.String(12), nullable=False, default="initiated", index=True)  # initiated|pending|success|failed|expired|review
    merchant_request_id = db.Column(db.String(64), nullable=True)
    checkout_request_id = db.Column(db.String(80), unique=True, nullable=True)
    mpesa_receipt = db.Column(db.String(32), unique=True, nullable=True)
    result_code = db.Column(db.String(20), nullable=True)
    result_desc = db.Column(db.String(300), nullable=True)
    note = db.Column(db.String(300), nullable=False, default="")
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_query_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    path = db.relationship("Path")

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "status": self.status,
            "method": self.method,
            "receipt": self.mpesa_receipt,
            "phone": ("*" * 6 + self.phone[-3:]) if self.phone else None,
            "note": self.note,
            "result_desc": self.result_desc,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Refund(db.Model):
    """A refund request. Money is sent back by the admin outside the app (M-Pesa/bank) and then recorded."""

    __tablename__ = "refunds"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    path_id = db.Column(db.Integer, db.ForeignKey("paths.id"), nullable=False)
    status = db.Column(db.String(12), nullable=False, default="requested", index=True)  # requested|approved|rejected|cancelled|paid_out
    reason = db.Column(db.String(500), nullable=False, default="")
    requested_amount = db.Column(db.Integer, nullable=False)
    policy_tier = db.Column(db.String(10), nullable=False, default="none")  # full | partial | none
    eligible_amount = db.Column(db.Integer, nullable=False, default=0)  # what the policy suggests
    approved_amount = db.Column(db.Integer, nullable=True)
    admin_note = db.Column(db.String(500), nullable=False, default="")
    decided_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    decided_at = db.Column(db.DateTime(timezone=True), nullable=True)
    payout_method = db.Column(db.String(40), nullable=True)
    payout_reference = db.Column(db.String(80), nullable=True)
    paid_out_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", foreign_keys=[user_id])
    path = db.relationship("Path")

    def to_dict(self):
        return {
            "id": self.id, "status": self.status, "reason": self.reason,
            "requested_amount": self.requested_amount, "policy_tier": self.policy_tier,
            "eligible_amount": self.eligible_amount, "approved_amount": self.approved_amount,
            "admin_note": self.admin_note, "payout_reference": self.payout_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "paid_out_at": self.paid_out_at.isoformat() if self.paid_out_at else None,
        }


class CheckIn(db.Model):
    """One scan of a workspace pass at the front desk."""

    __tablename__ = "checkins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    checked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    allowed = db.Column(db.Boolean, nullable=False)
    reason = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])


class AuditLog(db.Model):
    """Who did what to money, prices, access or refunds. Written for every admin action."""

    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(40), nullable=False, index=True)
    target = db.Column(db.String(80), nullable=False, default="")
    detail = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    admin = db.relationship("User", foreign_keys=[admin_id])
