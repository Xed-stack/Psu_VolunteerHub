"""
RBAC (Role-Based Access Control) Utilities for PSU Volunteer Hub
==================================================================
Provides decorators and helpers to restrict route access by user role.
"""
from functools import wraps
from flask import redirect, url_for, flash, g
from flask_login import current_user


def role_required(role: str, abort_403: bool = True):
    """Decorator to restrict routes by user role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            user_role = getattr(current_user, 'role', None)
            if user_role != role:
                if abort_403:
                    flash(f"Access denied. Requires {role} role.", "error")
                return redirect(url_for('dashboard'))
            g.user_role = user_role
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_only(abort_403: bool = True):
    """Convenience wrapper for @role_required('admin')"""
    return role_required('admin', abort_403=abort_403)


def coordinator_or_above(abort_403: bool = True):
    """Decorator for coordinators, directors, or admins only."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            user_role = getattr(current_user, 'role', None)
            allowed_roles = ['coordinator', 'director', 'admin']
            if user_role not in allowed_roles:
                if abort_403:
                    flash("Access denied. Requires coordinator or higher role.", "error")
                return redirect(url_for('dashboard'))
            g.user_role = user_role
            return f(*args, **kwargs)
        return decorated_function
    return decorator
