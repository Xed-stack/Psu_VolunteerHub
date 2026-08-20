"""
Volunteer Profile Routes for PSU Volunteer Hub
===============================================
Handles profile viewing/editing, participation history, and
profile-level analytics (impact stats, badges, level progress,
preferred categories, and event recommendations).
"""
from collections import Counter
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db
from app.models.user import VolunteerProfile, Skill, Interest
from app.models.event import Registration, Event, Attendance
from app.recommendation.analytics import AnalyticsAggregator
from app.recommendation.engine import get_recommendations
from app.utils.decorators import role_required

volunteer_bp = Blueprint('volunteer', __name__, url_prefix='')


def _sync_terms(model_cls, names, existing_lookup):
    """
    Given a comma-separated list of names, return the list of ORM objects
    to attach to a relationship — reusing existing rows where they match,
    creating new ones where they don't. Mirrors Event.required_skills setter.
    """
    objects = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        obj = existing_lookup(name)
        if not obj:
            obj = model_cls(name=name)
            db.session.add(obj)
        objects.append(obj)
    return objects


def _level_progress(total_hours):
    """Compute tier name, progress percent within tier, and hours to next tier."""
    tiers = [
        ('Bronze', 'Newcomer', 0, 10),
        ('Silver', 'Active Volunteer', 10, 50),
        ('Gold', 'Community Leader', 50, 100),
        ('Platinum', 'Champion', 100, None),
    ]
    for cert, label, low, high in tiers:
        if high is None or total_hours < high:
            if high is None:
                return {'cert_level': cert, 'label': label, 'percent': 100, 'hours_to_next': 0}
            percent = round(((total_hours - low) / (high - low)) * 100, 1)
            return {
                'cert_level': cert, 'label': label,
                'percent': max(0.0, min(percent, 100.0)),
                'hours_to_next': round(high - total_hours, 1),
            }


def _compute_badges(total_hours, total_activities, distinct_categories):
    """Derive earned badges from actual participation data."""
    badges = [
        {'name': 'Helping Hand', 'icon': 'volunteer_activism',
            'earned': total_activities >= 1},
        {'name': '100+ Hours', 'icon': 'timer', 'earned': total_hours >= 100},
        {'name': 'Category Explorer', 'icon': 'travel_explore',
            'earned': distinct_categories >= 3},
        {'name': 'Legendary', 'icon': 'star', 'earned': total_hours >= 200},
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

        skill_names = request.form.get('skills', '').split(',')
        interest_names = request.form.get('interests', '').split(',')

        current_user.skills = _sync_terms(
            Skill, skill_names, lambda n: Skill.query.filter_by(name=n).first())
        current_user.interests = _sync_terms(
            Interest, interest_names, lambda n: Interest.query.filter_by(name=n).first())

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('volunteer.profile_page'))

    # ── Analytics: impact stats ─────────────────────────────────────────
    total_hours = db.session.query(db.func.sum(Attendance.hours_completed))\
        .filter_by(user_id=current_user.id).scalar() or 0.0
    total_activities = Registration.query.filter_by(
        user_id=current_user.id).count()

    level = _level_progress(total_hours)

    distinct_categories = db.session.query(Event.category).join(
        Attendance, Attendance.event_id == Event.id
    ).filter(Attendance.user_id == current_user.id, Attendance.status == 'present')\
     .distinct().count()

    badges = _compute_badges(
        total_hours, total_activities, distinct_categories)
    preferred_categories = _preferred_categories(current_user.id)

    user_stats = {
        'total_hours': round(total_hours, 1),
        'total_activities': total_activities,
        'cert_level': level['cert_level'],
        'level_label': level['label'],
        'level_percent': level['percent'],
        'hours_to_next': level['hours_to_next'],
    }

    # ── Analytics: registration history (for the table on this page) ───
    registrations = Registration.query.filter_by(user_id=current_user.id)\
        .order_by(Registration.registered_at.desc()).limit(5).all()

    # ── Analytics: Jaccard-based recommendations ────────────────────────
    recommendations = get_recommendations(profile, top_n=3) if profile else []

    return render_template(
        'volunteer/Volunteer_Profile.html',
        profile=profile,
        user_stats=user_stats,
        badges=badges,
        preferred_categories=preferred_categories,
        registrations=registrations,
        recommendations=recommendations,
    )


@volunteer_bp.route('/volunteer_analytics')
@login_required
@role_required('volunteer')
def analytics():
    kpi_cards = AnalyticsAggregator.kpi_summary()
    campus_data = AnalyticsAggregator.campus_stats()
    demographics = AnalyticsAggregator.role_demographics()
    trend_data = AnalyticsAggregator.trend_data()
    heatmap_data = AnalyticsAggregator.heatmap_data()
    return render_template('volunteer/Volunteer_analytics.html',
                           kpi_cards=kpi_cards,
                           campus_data=campus_data,
                           demographics=demographics,
                           trend_data=trend_data,
                           heatmap_data=heatmap_data)
