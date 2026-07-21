"""
Event Management Models for PSU Volunteer Hub
==============================================
Models for activities/events, registrations, attendance tracking,
milestones, campuses, recommendation logs, and analytics summaries.
"""
from datetime import datetime
from app.models import db
from app.models.user import Skill

# Junction table for event required skills (3NF)
event_skills = db.Table(
    'event_skills',
    db.Column('event_id', db.Integer, db.ForeignKey(
        'events.id', ondelete='CASCADE'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey(
        'skills.id', ondelete='CASCADE'), primary_key=True)
)


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
    slots = db.Column(db.Integer, default=0)
    campus_id = db.Column(db.Integer, db.ForeignKey(
        'campuses.id', ondelete='SET NULL'))

    # Relationships
    campus = db.relationship('Campus', backref='events', lazy=True)
    registrations = db.relationship(
        'Registration', backref='event', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship(
        'Attendance', backref='event', lazy=True, cascade='all, delete-orphan')
    milestones = db.relationship(
        'Milestone', backref='event', lazy=True, cascade='all, delete-orphan')

    # 3NF Skills relationship
    required_skills_rel = db.relationship(
        'Skill', secondary=event_skills, backref=db.backref('events', lazy='dynamic'))

    @property
    def required_skills(self) -> str:
        """Backward-compatible helper string for UI templates."""
        return ", ".join([s.name for s in self.required_skills_rel])

    @required_skills.setter
    def required_skills(self, skills_string: str):
        if not skills_string:
            self.required_skills_rel = []
            return

        # Explicitly ensure this event object is registered in the session
        # before running queries to avoid autoflush warnings.
        if db.session and self not in db.session:
            db.session.add(self)

        from app.models.user import Skill
        names = [s.strip() for s in skills_string.split(',') if s.strip()]

        skills_objects = []
        for name in names:
            skill = Skill.query.filter_by(name=name).first()
            if not skill:
                skill = Skill(name=name)
                db.session.add(skill)
            skills_objects.append(skill)

        self.required_skills_rel = skills_objects

    def slots_remaining(self) -> int:
        """Return number of available slots (0 if unlimited or full)."""
        if self.slots <= 0:
            return 0
        confirmed = sum(1 for r in self.registrations if r.status in (
            'confirmed', 'completed'))
        return max(0, self.slots - confirmed)


class Registration(db.Model):
    """
    Tracks volunteer registration for a specific event.
    """
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey(
        'events.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'confirmed', 'completed',
                'cancelled', name='registration_statuses'),
        default='pending'
    )
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint(
        'user_id', 'event_id', name='uk_user_event'),)

    @property
    def is_confirmed(self) -> bool:
        return self.status in ('confirmed', 'completed')


class Attendance(db.Model):
    """
    Tracks attendance and hours contributed at an event.
    """
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey(
        'registrations.id', ondelete='SET NULL'))
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey(
        'events.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('present', 'absent', 'excused',
                       name='attendance_statuses'), default='present')
    hours_completed = db.Column(db.Float, default=0.0)


class Milestone(db.Model):
    """
    Stores milestone uploads (photos, documents) for events.
    """
    __tablename__ = 'milestones'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey(
        'events.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
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
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey(
        'events.id', ondelete='CASCADE'), nullable=False)
    similarity_score = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class AnalyticsSummary(db.Model):
    """
    Pre-calculated aggregate metrics for dashboard performance.
    """
    __tablename__ = 'analytics_summaries'

    id = db.Column(db.Integer, primary_key=True)
    campus_id = db.Column(db.Integer, db.ForeignKey(
        'campuses.id', ondelete='SET NULL'))
    metric_type = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(50), nullable=False)
