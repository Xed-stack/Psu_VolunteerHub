"""
Volunteer Profile Routes for PSU Volunteer Hub
===============================================
Handles profile viewing/editing, participation history, and
profile-level analytics (impact stats, badges, level progress,
preferred categories, and event recommendations).
"""
from collections import Counter
import os
import uuid

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app)
from flask_login import login_required, current_user
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from app.models import db
from app.models.user import VolunteerProfile, Skill, Interest
from app.models.event import Registration, Event, Attendance
from app.recommendation.analytics import AnalyticsAggregator
from app.recommendation.engine import get_recommendations
from app.utils.decorators import role_required

volunteer_bp = Blueprint('volunteer', __name__, url_prefix='')


def _selected_records(model, values):
    ids = {int(value) for value in values if str(value).isdigit()}
    return model.query.filter(model.id.in_(ids)).all() if ids else []


def _save_profile_image(file):
    if not file or not file.filename:
        return None
    extension = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
    if extension not in {'jpg', 'jpeg', 'png', 'webp'}:
        raise ValueError('Profile image must be JPEG, PNG, or WebP.')
    file.stream.seek(0, os.SEEK_END)
    if file.stream.tell() > 3 * 1024 * 1024:
        raise ValueError('Profile image must be 3 MB or smaller.')
    file.stream.seek(0)
    try:
        with Image.open(file.stream) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError('Profile image is not a valid image file.')
    finally:
        file.stream.seek(0)
    directory = os.path.join(current_app.static_folder, 'uploads', 'profiles')
    os.makedirs(directory, exist_ok=True)
    filename = f'{uuid.uuid4().hex}.{extension}'
    file.save(os.path.join(directory, filename))
    return f'uploads/profiles/{filename}'


def _level_progress(total_activities):
    """Compute volunteer progress from completed participation counts."""
    tiers = [
        ('Bronze', 'Newcomer', 0, 3),
        ('Silver', 'Active Volunteer', 3, 10),
        ('Gold', 'Community Leader', 10, 20),
        ('Platinum', 'Champion', 20, None),
    ]
    for cert, label, low, high in tiers:
        if high is None or total_activities < high:
            if high is None:
                return {'cert_level': cert, 'label': label, 'percent': 100}
            percent = round(((total_activities - low) / (high - low)) * 100, 1)
            return {
                'cert_level': cert, 'label': label,
                'percent': max(0.0, min(percent, 100.0)),
            }


def _compute_badges(total_activities, distinct_categories):
    """Derive earned badges from actual participation data."""
    badges = [
        {'name': 'Helping Hand', 'icon': 'volunteer_activism',
            'earned': total_activities >= 1},
        {'name': 'Active Volunteer', 'icon': 'diversity_3', 'earned': total_activities >= 5},
        {'name': 'Category Explorer', 'icon': 'travel_explore',
            'earned': distinct_categories >= 3},
        {'name': 'Community Champion', 'icon': 'star', 'earned': total_activities >= 15},
    ]
    return badges


def _preferred_categories(user_id, top_n=3):
    """Most frequent event categories among the user's attended events."""
    rows = db.session.query(Event.category).join(
        Attendance, Attendance.event_id == Event.id
    ).filter(Attendance.user_id == user_id, Attendance.status == 'present').all()
    counts = Counter(r[0] for r in rows if r[0])
    return [name for name, _ in counts.most_common(top_n)]


@volunteer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('volunteer')
def profile_page():
    profile = VolunteerProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        if not profile:
            profile = VolunteerProfile(user_id=current_user.id)
            db.session.add(profile)

        skills = _selected_records(Skill, request.form.getlist('skills'))
        interests = _selected_records(Interest, request.form.getlist('interests'))
        if not skills or not interests:
            flash('Select at least one skill and one interest.', 'error')
            return redirect(url_for('volunteer.profile_page'))
        current_user.skills = skills
        current_user.interests = interests

        image = request.files.get('profile_image')
        try:
            image_path = _save_profile_image(image)
        except ValueError as exc:
            flash(str(exc), 'error')
            return redirect(url_for('volunteer.profile_page'))
        if image_path:
            old_path = current_user.profile_image_path
            current_user.profile_image_path = image_path
            current_user.profile_image_name = secure_filename(image.filename)
            if old_path:
                old_file = os.path.join(current_app.static_folder, old_path)
                if os.path.isfile(old_file):
                    os.remove(old_file)

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('volunteer.profile_page'))

    # ── Analytics: impact stats ─────────────────────────────────────────
    total_activities = Registration.query.filter_by(
        user_id=current_user.id).count()

    level = _level_progress(total_activities)

    distinct_categories = db.session.query(Event.category).join(
        Attendance, Attendance.event_id == Event.id
    ).filter(Attendance.user_id == current_user.id, Attendance.status == 'present')\
     .distinct().count()

    badges = _compute_badges(total_activities, distinct_categories)
    preferred_categories = _preferred_categories(current_user.id)

    user_stats = {
        'total_activities': total_activities,
        'cert_level': level['cert_level'],
        'level_label': level['label'],
        'level_percent': level['percent'],
    }

    # ── Analytics: registration history (for the table on this page) ───
    registrations = Registration.query.filter_by(user_id=current_user.id)\
        .order_by(Registration.registered_at.desc()).limit(5).all()

    # ── Analytics: cosine-similarity recommendations ────────────────────
    recommendations = get_recommendations(
        profile, top_n=3, campus_id=current_user.campus_id)

    return render_template(
        'volunteer/Volunteer_Profile.html',
        profile=profile,
        user_stats=user_stats,
        badges=badges,
        preferred_categories=preferred_categories,
        registrations=registrations,
        recommendations=recommendations,
        skill_catalog=Skill.query.order_by(Skill.name).all(),
        interest_catalog=Interest.query.order_by(Interest.name).all(),
    )


@volunteer_bp.route('/profile/image/remove', methods=['POST'])
@login_required
@role_required('volunteer')
def remove_profile_image():
    path = current_user.profile_image_path
    current_user.profile_image_path = None
    current_user.profile_image_name = None
    db.session.commit()
    if path:
        file_path = os.path.join(current_app.static_folder, path)
        if os.path.isfile(file_path):
            os.remove(file_path)
    flash('Profile image removed.', 'success')
    return redirect(url_for('volunteer.profile_page'))


@volunteer_bp.route('/volunteer_analytics')
@login_required
@role_required('volunteer')
def analytics():
    """Compatibility redirect: volunteers do not receive global analytics."""
    return redirect(url_for('events.volunteer_dash'))
