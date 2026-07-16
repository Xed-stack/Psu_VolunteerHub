"""
Event Management Models for PSU Volunteer Hub
==============================================
Models for activities/events, registrations, attendance tracking,
milestones, campuses, recommendation logs, and analytics summaries.
"""
from datetime import datetime
from app.models import db


class Event(db.Model):
    """
    Represents a volunteer activity/event posted by coordinators.
    """
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    category = db.Column(db.String(50), default='General')
    location = db.Column(db.String(500), default='')
    required_skills = db.Column(db.Text, default='')
    slots = db.Column(db.Integer, default=0)
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'))

    campus = db.relationship('Campus', backref='events', lazy=True)
    registrations = db.relationship('Registration', backref='event', lazy=True)
    attendance_records = db.relationship('Attendance', backref='event', lazy=True)

    def slots_remaining(self) -> int:
        """Return number of available slots (0 if unlimited or full)."""
        if self.slots <= 0:
            return 0
        confirmed = sum(1 for r in self.registrations if r.status == 'confirmed')
        return max(0, self.slots - confirmed)


class Registration(db.Model):
    """
    Tracks volunteer registration for a specific event.
    """
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    status = db.Column(db.String(20), default='pending')
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_confirmed(self) -> bool:
        return self.status in ('confirmed', 'completed')


class Attendance(db.Model):
    """
    Tracks attendance and hours contributed at an event.
    """
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    status = db.Column(db.String(20), default='present')
    hours_completed = db.Column(db.Float, default=0.0)


class Milestone(db.Model):
    """
    Stores milestone uploads (photos, documents) for events.
    """
    __tablename__ = 'milestones'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    filename = db.Column(db.String(255))
    upload_path = db.Column(db.String(500), default='')
    category = db.Column(db.String(100), default='photo')


class Campus(db.Model):
    """
    Represents PSU campuses for organizational purposes.
    """
    __tablename__ = 'campuses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, default='')

    def __repr__(self) -> str:
        return f"Campus(id={self.id}, name='{self.name}')"


class RecommendationLog(db.Model):
    """
    Logs recommendation system activity for analysis.
    """
    __tablename__ = 'recommendation_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    similarity_score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class AnalyticsSummary(db.Model):
    """
    Pre-calculated aggregate metrics for dashboard performance.
    """
    __tablename__ = 'analytics_summaries'

    id = db.Column(db.Integer, primary_key=True)
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'))
    metric_type = db.Column(db.String(100))
    value = db.Column(db.Float)
    period = db.Column(db.String(50))
