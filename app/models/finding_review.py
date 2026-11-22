"""Review decisions are separate from the institutional facts they assess."""
from datetime import datetime
from app.models import db


class FindingReview(db.Model):
    __tablename__ = 'finding_reviews'
    id = db.Column(db.Integer, primary_key=True)
    finding_key = db.Column(db.String(64), nullable=False, unique=True)
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'), nullable=True, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='SET NULL'), index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    activity_date = db.Column(db.DateTime)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    finding_type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(24), nullable=False, default='needs_review', index=True)
    fingerprint = db.Column(db.String(64), nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    scope = db.Column(db.JSON, nullable=False)
    assessment = db.Column(db.Text, nullable=False, default='')
    recommendation = db.Column(db.String(40), nullable=False, default='')
    closure_reason = db.Column(db.String(40), nullable=False, default='')
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FindingReviewEvent(db.Model):
    __tablename__ = 'finding_review_events'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('finding_reviews.id'), nullable=False, index=True)
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'), nullable=True, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    actor_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(32), nullable=False, index=True)
    content = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
