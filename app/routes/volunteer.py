"""
Volunteer Profile Routes for PSU Volunteer Hub
===============================================
Handles profile viewing/editing and participation history.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db
from app.models.user import VolunteerProfile
from app.models.event import Registration, Event, Attendance

volunteer_bp = Blueprint('volunteer', __name__, url_prefix='')


@volunteer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_page():
    profile = VolunteerProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        if not profile:
            profile = VolunteerProfile(user_id=current_user.id)
            db.session.add(profile)

        skills = request.form.get('skills', '').strip()
        interests = request.form.get('interests', '').strip()

        profile.skills = skills
        profile.interests = interests
        db.session.commit()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('volunteer.profile_page'))

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
    return render_template('Volunteer_Profile.html', profile=profile, user_stats=user_stats)


@volunteer_bp.route('/certificates')
@login_required
def certificates():
    records = db.session.query(Attendance, Event).join(Event, Attendance.event_id == Event.id).filter(Attendance.user_id == current_user.id, Attendance.hours_completed > 0).all()
    certs = []
    for att, event in records:
        certs.append({'event_title': event.title, 'event_date': event.date, 'hours': att.hours_completed, 'status': 'earned'})
    return render_template('Volunteer_dash.html', certificates=certs, user_stats={}, recent_activity=[], upcoming_schedule=[], certification={})


@volunteer_bp.route('/history')
@login_required
def history():
    profile = VolunteerProfile.query.filter_by(user_id=current_user.id).first()
    registrations = Registration.query.filter_by(user_id=current_user.id).order_by(Registration.registered_at.desc()).all()
    total_hours = db.session.query(db.func.sum(Attendance.hours_completed)).filter_by(user_id=current_user.id).scalar() or 0.0
    total_activities = len(registrations)
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
    return render_template('Volunteer_Profile.html', registrations=registrations, profile=profile, user_stats=user_stats)