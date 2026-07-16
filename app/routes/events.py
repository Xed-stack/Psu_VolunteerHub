"""
Events Routes for PSU Volunteer Hub
=====================================
Manages event listings, registrations, and the volunteer dashboard.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db
from app.models.user import VolunteerProfile
from app.models.event import Event, Registration, Attendance, Campus
from app.recommendation.engine import get_recommendations
from datetime import datetime

events_bp = Blueprint('events', __name__, url_prefix='')


@events_bp.route('/opportunities')
def opportunities():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    campus_id = request.args.get('campus', type=int)
    category = request.args.get('category', type=str) or None
    search = request.args.get('search', type=str) or None
    query = Event.query.filter(Event.date >= datetime.now(), Event.slots > 0)
    if campus_id:
        query = query.filter(Event.campus_id == campus_id)
    if category:
        query = query.filter(Event.category == category)
    if search:
        like = f'%{search}%'
        query = query.filter(Event.title.ilike(like) | Event.description.ilike(like))
    query = query.order_by(Event.date.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items
    campuses = Campus.query.all()
    return render_template('Volunteer_opportunities.html',
                           events=events, campuses=campuses,
                           current_page=pagination.page,
                           total_pages=pagination.pages,
                           total_count=pagination.total,
                           selected_campus=campus_id,
                           selected_category=category,
                           selected_status='upcoming',
                           search_query=search)


@events_bp.route('/opportunities/register/<int:event_id>', methods=['POST'])
@login_required
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)
    existing = Registration.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing:
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('events.opportunities'))
    if event.slots > 0 and event.slots_remaining() <= 0:
        flash('No available slots for this event.', 'error')
        return redirect(url_for('events.opportunities'))
    registration = Registration(user_id=current_user.id, event_id=event_id, status='confirmed')
    db.session.add(registration)
    db.session.commit()
    flash('Successfully registered for the event!', 'success')
    return redirect(url_for('events.opportunities'))


@events_bp.route('/volunteer_dash')
@login_required
def volunteer_dash():
    profile = VolunteerProfile.query.filter_by(user_id=current_user.id).first()
    upcoming_events = Event.query.filter(Event.date >= datetime.now()).order_by(Event.date.asc()).all()
    recommendations = get_recommendations(profile, upcoming_events)
    total_hours = db.session.query(db.func.sum(Attendance.hours_completed)).filter_by(user_id=current_user.id).scalar() or 0.0
    total_activities = Registration.query.filter_by(user_id=current_user.id).count()
    hours_val = total_hours or 0
    if hours_val < 10:
        cert_level = 'Bronze'
    elif hours_val < 50:
        cert_level = 'Silver'
    elif hours_val < 100:
        cert_level = 'Gold'
    else:
        cert_level = 'Platinum'
    user_stats = {'total_hours': round(total_hours, 1), 'total_activities': total_activities, 'cert_level': cert_level}
    upcoming = Registration.query.filter_by(user_id=current_user.id).join(Event).filter(Event.date >= datetime.now()).order_by(Event.date.asc()).limit(5).all()
    recent_activity = Registration.query.filter_by(user_id=current_user.id).order_by(Registration.registered_at.desc()).limit(5).all()
    upcoming_schedule = [{'event': r.event, 'date': r.event.date} for r in upcoming]
    certification = {'level': cert_level, 'hours': round(total_hours, 1), 'next_level': 'Silver' if cert_level == 'Bronze' else 'Gold' if cert_level == 'Silver' else 'Platinum' if cert_level == 'Gold' else 'Max'}
    return render_template('Volunteer_dash.html',
                           recommendations=recommendations,
                           user_stats=user_stats,
                           recent_activity=recent_activity,
                           upcoming_schedule=upcoming_schedule,
                           certification=certification)
