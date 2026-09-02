"""
Events Routes for PSU Volunteer Hub
=====================================
Manages event listings, registrations, and the volunteer dashboard.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models import db
from app.models.user import VolunteerProfile
from app.models.event import (Event, Registration, Attendance, Campus,
                             ExternalParticipant)
from app.recommendation.engine import get_recommendations, bootstrap_from_event
from app.utils.decorators import role_required
from app.models.notification import notify, notify_campus_coordinators
from datetime import datetime

events_bp = Blueprint('events', __name__, url_prefix='')


def _upsert_external_participant(id_number, name=None, contact_number=None,
                                 address=None, email=None):
    """Find an existing outsider by ID number or create a new record."""
    id_number = (id_number or '').strip()
    participant = ExternalParticipant.query.filter_by(id_number=id_number).first()
    if participant is None:
        participant = ExternalParticipant(id_number=id_number)
        db.session.add(participant)
    # Optional fields: populate when provided, never overwrite with blanks.
    if name and not participant.name:
        participant.name = name.strip()
    if contact_number and not participant.contact_number:
        participant.contact_number = contact_number.strip()
    if address and not participant.address:
        participant.address = address.strip()
    if email and not participant.email:
        participant.email = email.strip()
    db.session.flush()
    return participant


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
        query = query.filter(Event.title.ilike(
            like) | Event.description.ilike(like))
    query = query.order_by(Event.date.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items
    campuses = Campus.query.all()
    # Data-driven category filter: distinct categories actually in use,
    # so the dropdown never offers options that return zero results.
    categories = [row[0] for row in db.session.query(
        Event.category).distinct().order_by(Event.category).all() if row[0]]
    return render_template('volunteer/Volunteer_opportunities.html',
                           events=events, campuses=campuses,
                           categories=categories,
                           current_page=pagination.page,
                           total_pages=pagination.pages,
                           total_count=pagination.total,
                           selected_campus=campus_id,
                           selected_category=category,
                           selected_status='upcoming',
                           search_query=search)


@events_bp.route('/opportunities/register/<int:event_id>', methods=['POST'])
@login_required
@role_required('volunteer')
def register_for_event(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    existing = Registration.query.filter_by(
        user_id=current_user.id, event_id=event_id).first()
    if existing:
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('events.opportunities'))
    if event.slots > 0 and event.slots_remaining() <= 0:
        flash('No available slots for this event.', 'error')
        return redirect(url_for('events.opportunities'))
    registration = Registration(
        user_id=current_user.id, event_id=event_id, status='confirmed')
    db.session.add(registration)
    db.session.commit()
    bootstrap_from_event(current_user, event)
    notify_campus_coordinators(
        event.campus_id,
        title=f'New registration: {event.title}',
        message=f'{current_user.name or current_user.email} registered for '
                f'"{event.title}".',
        notification_type='registration',
        related_event_id=event.id)
    flash('Successfully registered for the event!', 'success')
    return redirect(url_for('events.opportunities'))


@events_bp.route('/volunteer_dash')
@login_required
@role_required('volunteer')
def volunteer_dash():
    profile = VolunteerProfile.query.filter_by(user_id=current_user.id).first()
    upcoming_events = Event.query.filter(
        Event.date >= datetime.now()).order_by(Event.date.asc()).all()
    recommendations = get_recommendations(
        profile, upcoming_events, campus_id=current_user.campus_id)
    total_hours = db.session.query(db.func.sum(Attendance.hours_completed)).filter_by(
        user_id=current_user.id).scalar() or 0.0
    total_activities = Registration.query.filter_by(
        user_id=current_user.id).count()
    hours_val = total_hours or 0
    if hours_val < 10:
        cert_level = 'Bronze'
    elif hours_val < 50:
        cert_level = 'Silver'
    elif hours_val < 100:
        cert_level = 'Gold'
    else:
        cert_level = 'Platinum'
    user_stats = {'total_hours': round(
        total_hours, 1), 'total_activities': total_activities, 'cert_level': cert_level}
    upcoming = Registration.query.filter_by(user_id=current_user.id).join(Event).filter(
        Event.date >= datetime.now()).order_by(Event.date.asc()).limit(5).all()
    recent_activity = Registration.query.filter_by(user_id=current_user.id).order_by(
        Registration.registered_at.desc()).limit(5).all()
    upcoming_schedule = [{'event': r.event, 'date': r.event.date}
                         for r in upcoming]
    certification = {'level': cert_level, 'hours': round(total_hours, 1), 'next_level': 'Silver' if cert_level ==
                      'Bronze' else 'Gold' if cert_level == 'Silver' else 'Platinum' if cert_level == 'Gold' else 'Max'}
    return render_template('volunteer/Volunteer_dash.html',
                           recommendations=recommendations,
                           user_stats=user_stats,
                           recent_activity=recent_activity,
                           upcoming_schedule=upcoming_schedule,
                           certification=certification)


@events_bp.route('/event/<int:event_id>/join', methods=['GET', 'POST'])
def event_join(event_id):
    """Public activity join workflow.

    Asks whether the participant is currently from PSU. PSU volunteers use the
    existing authenticated registration flow; outsiders complete the outsider
    form, which creates an ExternalParticipant + Registration (never a User,
    never a privileged role).
    """
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if request.method == 'POST':
        from_psu = request.form.get('from_psu', '').strip()
        if from_psu == 'yes':
            return redirect(url_for(
                'auth.login',
                next=url_for('events.register_for_event', event_id=event.id)))
        # Outsider path
        id_number = request.form.get('id_number', '').strip()
        if not id_number:
            flash('ID number is required for outsider registration.', 'error')
            return render_template(
                'events/event_join.html', event=event, external_form=True), 400
        participant = _upsert_external_participant(
            id_number,
            name=request.form.get('name', '').strip(),
            contact_number=request.form.get('contact_number', '').strip(),
            address=request.form.get('address', '').strip(),
            email=request.form.get('email', '').strip())
        # One registration per outsider per event.
        existing = Registration.query.filter_by(
            external_participant_id=participant.id, event_id=event.id).first()
        if existing is None:
            db.session.add(Registration(
                external_participant_id=participant.id, event_id=event.id,
                status='confirmed'))
            db.session.commit()
            notify_campus_coordinators(
                event.campus_id,
                title=f'New external volunteer: {event.title}',
                message=f'An external volunteer ({participant.name or participant.id_number}) '
                        f'registered for "{event.title}".',
                notification_type='external_registration',
                related_event_id=event.id)
        flash('You are registered for this activity as an external volunteer.',
              'success')
        return redirect(url_for('events.opportunities'))

    external_form = request.args.get('external') == '1'
    return render_template(
        'events/event_join.html', event=event, external_form=external_form)
