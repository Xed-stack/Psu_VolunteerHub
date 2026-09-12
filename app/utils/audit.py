"""Small shared helper for recording append-only audit entries."""
import json

from flask_login import current_user

from app.models import db
from app.models.audit import AuditLog


def log_activity(action, target, details=None):
    """Queue an audit entry in the caller's existing transaction."""
    db.session.add(AuditLog(
        actor_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        target_type=type(target).__name__,
        target_id=getattr(target, 'id', None),
        details=json.dumps(details, ensure_ascii=False) if details else None,
    ))
