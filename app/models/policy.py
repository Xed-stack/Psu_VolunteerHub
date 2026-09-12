"""Versioned system-wide terms and their user acceptances."""
from datetime import datetime

from app.models import db


class TermsRevision(db.Model):
    __tablename__ = 'terms_revisions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    version = db.Column(db.String(30), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    published_by_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='SET NULL'), nullable=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    published_by = db.relationship('User', backref=db.backref(
        'published_terms', lazy=True))


class TermsAcceptance(db.Model):
    __tablename__ = 'terms_acceptances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), nullable=False)
    revision_id = db.Column(db.Integer, db.ForeignKey(
        'terms_revisions.id', ondelete='CASCADE'), nullable=False)
    accepted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('terms_acceptances', lazy=True))
    revision = db.relationship('TermsRevision', backref=db.backref(
        'acceptances', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'revision_id', name='uq_user_terms_revision'),
    )


class PrivacyRevision(db.Model):
    __tablename__ = 'privacy_revisions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    version = db.Column(db.String(30), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    published_by_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='SET NULL'), nullable=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PrivacyAcknowledgement(db.Model):
    __tablename__ = 'privacy_acknowledgements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    revision_id = db.Column(db.Integer, db.ForeignKey('privacy_revisions.id', ondelete='CASCADE'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'revision_id', name='uq_user_privacy_revision'),
    )


class ParticipationAgreementRevision(db.Model):
    """Administrator-managed fallback for live events without custom text."""
    __tablename__ = 'participation_agreement_revisions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    version = db.Column(db.String(30), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    published_by_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='SET NULL'), nullable=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
