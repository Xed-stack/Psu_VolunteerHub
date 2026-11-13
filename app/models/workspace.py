"""Persistent campus workspaces and private activity documents."""
from datetime import datetime
from app.models import db


class FormDraft(db.Model):
    __tablename__ = 'form_drafts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id', ondelete='CASCADE'))
    key = db.Column(db.String(160), nullable=False)
    payload = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'key', name='uq_form_draft_user_key'),)


class PartnerAgency(db.Model):
    __tablename__ = 'partner_agencies'
    id = db.Column(db.Integer, primary_key=True)
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id', ondelete='RESTRICT'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    contact_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    agreements = db.relationship('PartnerAgreement', backref='agency', lazy='selectin')


class PartnerAgreement(db.Model):
    __tablename__ = 'partner_agreements'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('partner_agencies.id', ondelete='RESTRICT'), nullable=False)
    reference = db.Column(db.String(150), nullable=False)
    valid_from = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    document = db.Column(db.JSON, nullable=False)


class ExternalGroup(db.Model):
    __tablename__ = 'external_groups'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='RESTRICT'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
