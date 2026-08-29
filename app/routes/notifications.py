"""In-app notification routes.

Notifications belong to authenticated PSU users only. A user may read/update
only their own notifications. Cross-user access is denied.
"""
from flask import (Blueprint, render_template, redirect, url_for, request,
                   flash, abort)
from flask_login import login_required, current_user

from app.models.notification import Notification
from app.models import db

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
@login_required
def list_notifications():
    notes = (Notification.query
             .filter_by(user_id=current_user.id)
             .order_by(Notification.created_at.desc())
             .all())
    unread = sum(1 for n in notes if not n.is_read)
    return render_template('notifications/list.html',
                           notifications=notes, unread=unread)


@notifications_bp.route('/notifications/<int:notification_id>/read',
                        methods=['POST'])
@login_required
def mark_read(notification_id):
    note = db.session.get(Notification, notification_id)
    if note is None:
        abort(404)
    if note.user_id != current_user.id:
        flash('You cannot modify that notification.', 'error')
        return redirect(url_for('notifications.list_notifications'))
    note.is_read = True
    db.session.commit()
    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    (Notification.query
     .filter_by(user_id=current_user.id, is_read=False)
     .update({'is_read': True}))
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.list_notifications'))
