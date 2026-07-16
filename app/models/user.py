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


class User(UserMixin, db.Model):
    """
    Core user model with authentication and RBAC.

    Attributes:
        id: Primary key
        name: User's full name
        email: Unique identifier for login
        password_hash: Hashed password (not stored in plain text)
        role: One of 'volunteer', 'coordinator', 'director', or 'admin'
        campus_id: Foreign key to campus table (optional)
        is_active: Account status flag
        created_at: Timestamp of account creation
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    id_number = db.Column(db.String(50), default='')
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='volunteer')
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'))
    _is_active = db.Column('is_active', db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registrations = db.relationship('Registration', backref='user', lazy=True)
    attendance_records = db.relationship('Attendance', backref='user', lazy=True)

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
    Stores skills, interests, and past participation history.
    """
    __tablename__ = 'volunteer_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    skills = db.Column(db.Text, default='')
    interests = db.Column(db.Text, default='')
    past_participation = db.Column(db.JSON, default=list)

    @property
    def skill_list(self) -> list:
        """Return skills as a list for easy iteration."""
        return [s.strip() for s in self.skills.split(',') if s.strip()] if self.skills else []

    @property
    def interest_list(self) -> list:
        """Return interests as a list for easy iteration."""
        return [i.strip() for i in self.interests.split(',') if i.strip()] if self.interests else []

    def __repr__(self) -> str:
        return f"VolunteerProfile(id={self.id}, user_id={self.user_id})"


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, default='')
