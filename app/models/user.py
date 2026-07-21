"""
User Models for PSU Volunteer Hub
==================================
Core user management with role-based access control (RBAC).
Supports 4 user roles: volunteer, coordinator, director, admin.
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.models import db

# ----------------------------------------------------------------------
# Junction Tables (3NF Normalization for Skills and Interests)
# ----------------------------------------------------------------------
user_skills = db.Table(
    'user_skills',
    db.Column('user_id', db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey(
        'skills.id', ondelete='CASCADE'), primary_key=True)
)

user_interests = db.Table(
    'user_interests',
    db.Column('user_id', db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('interest_id', db.Integer, db.ForeignKey(
        'interests.id', ondelete='CASCADE'), primary_key=True)
)


class Skill(db.Model):
    """Lookup table for standardized volunteer skills."""
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Skill {self.name}>"


class Interest(db.Model):
    """Lookup table for volunteer interests/categories."""
    __tablename__ = 'interests'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Interest {self.name}>"


class User(UserMixin, db.Model):
    """
    Core user model with authentication and RBAC.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    id_number = db.Column(db.String(50), default='')
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum('volunteer', 'coordinator', 'director',
                     'admin', name='user_roles'), default='volunteer')
    campus_id = db.Column(db.Integer, db.ForeignKey(
        'campuses.id', ondelete='SET NULL'))
    _is_active = db.Column('is_active', db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    registrations = db.relationship(
        'Registration', backref='user', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship(
        'Attendance', backref='user', lazy=True, cascade='all, delete-orphan')
    profile = db.relationship(
        'VolunteerProfile', backref='user', uselist=False, cascade='all, delete-orphan')

    # Many-to-Many Relationships for 3NF
    skills = db.relationship(
        'Skill', secondary=user_skills, backref=db.backref('users', lazy='dynamic'))
    interests = db.relationship(
        'Interest', secondary=user_interests, backref=db.backref('users', lazy='dynamic'))

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    @property
    def role_display_name(self) -> str:
        """Return human-readable name for user's role."""
        display_names = {
            'volunteer': 'Volunteer',
            'coordinator': 'Extension Coordinator',
            'director': 'Extension Director',
            'admin': 'Admin'
        }
        return display_names.get(self.role, self.role.title()) if self.role else 'Volunteer'

    def set_password(self, password: str) -> None:
        """Hash and store a new password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify if provided password matches stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"User(id={self.id}, name='{self.name}', role='{self.role}')"


class VolunteerProfile(db.Model):
    """
    Extended profile for volunteers.
    Stores past participation history (JSON).
    """
    __tablename__ = 'volunteer_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id', ondelete='CASCADE'), unique=True, nullable=False)
    past_participation = db.Column(db.JSON, default=list)

    @property
    def skill_list(self) -> list:
        """Returns skills attached to the parent user model."""
        return [s.name for s in self.user.skills] if self.user else []

    @property
    def interest_list(self) -> list:
        """Returns interests attached to the parent user model."""
        return [i.name for i in self.user.interests] if self.user else []

    def __repr__(self) -> str:
        return f"VolunteerProfile(id={self.id}, user_id={self.user_id})"


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, default='')
