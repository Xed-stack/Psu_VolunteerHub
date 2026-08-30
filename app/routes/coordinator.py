"""
Coordinator Routes for PSU Volunteer Hub
==========================================
Manages event creation, attendance tracking, and coordinator dashboard.
"""
import os
import uuid
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, abort
from flask_login import login_required, current_user
from app.models import db
from app.models.event import Event, Registration, Attendance, Campus, Milestone
from app.utils.decorators import role_required
from app.models.notification import notify_campus_coordinators
from app.models.user import SystemSetting
from app.recommendation.analytics import AnalyticsAggregator
from app.reports import (
    build_events_report, render_csv, render_pdf, ReportError)
from datetime import datetime, timedelta

coordinator_bp = Blueprint('coordinator', __name__, url_prefix='')

EVENT_COVER_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
EVENT_COVER_MAX_BYTES = 5 * 1024 * 1024


def _max_event_slots():
    setting = SystemSetting.query.filter_by(key='max_slots_per_event').first()
    try:
        return max(1, int(setting.value)) if setting else 100
    except (TypeError, ValueError):
        return 100


def _save_event_cover(file):
    if not file or not file.filename:
        return None
    extension = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
    if extension not in EVENT_COVER_EXTENSIONS:
        raise ValueError('Cover image must be JPEG, PNG, or WebP.')
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > EVENT_COVER_MAX_BYTES:
        raise ValueError('Cover image must be 5 MB or smaller.')
    try:
        with Image.open(file.stream) as image:
            detected = (image.format or '').lower()
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError('Cover image is not a valid image file.')
    finally:
        file.stream.seek(0)
    valid_formats = {'jpeg': {'jpg', 'jpeg'}, 'png': {'png'}, 'webp': {'webp'}}
    if extension not in valid_formats.get(detected, set()):
        raise ValueError('Cover image extension does not match its contents.')
    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'events')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f'{uuid.uuid4().hex}.{extension}'
    file.save(os.path.join(upload_dir, filename))
    return {
        'path': f'uploads/events/{filename}',
        'original_name': secure_filename(file.filename),
    }


def _coordinator_campus_id():
    """Coordinator campus scope is always derived server-side, never from the
    request, so a forged ?campus_id= parameter cannot leak another campus."""
    return current_user.campus_id


@coordinator_bp.route('/coordinator_dash')
@login_required
@role_required('coordinator')
def coordinator_dash():
    status = request.args.get('status', 'upcoming')
    events = Event.query.filter_by(campus_id=current_user.campus_id)
    if status == 'upcoming':
        events = events.filter(Event.date >= datetime.now())
    elif status == 'past':
        events = events.filter(Event.date < datetime.now())
    events = events.order_by(Event.date.desc()).all()
    upcoming_count = sum(1 for e in events if e.date >= datetime.now())
    # Centralized campus-scoped participation metrics (Phase 18): keeps the
    # dashboard consistent with the analytics page, CSV and PDF exports.
    summary = AnalyticsAggregator.participation_summary(
        campus_id=current_user.campus_id)
    recent_activities = Registration.query.filter(
        Registration.event_id.in_([e.id for e in events])
    ).order_by(Registration.registered_at.desc()).limit(5).all() if events else []

    # Context the template needs but the route was not passing
    campus_name = current_user.campus.name if current_user.campus else 'Campus'

    return render_template('coordinator/Coordinator_dash.html',
                            events=events,
                            upcoming_count=upcoming_count,
                            total_volunteers=summary['unique_volunteers'],
                            attendance_rate=summary['attendance_rate'],
                            service_hours=summary['service_hours'],
                            registrations=summary['registrations'],
                            recent_activities=recent_activities,
                            selected_status=status,
                            campus_name=campus_name,
                            campus_total_hours=summary['service_hours'])


@coordinator_bp.route('/create_activity', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def create_activity():
    campuses = [current_user.campus] if current_user.campus else []
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        date_str = request.form.get('date', '').strip()
        location = request.form.get('location', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        category = request.form.get('category', 'General').strip()
        slots = request.form.get('slots', 0, type=int)
        max_slots = _max_event_slots()
        campus_id = current_user.campus_id
        if campus_id is None:
            flash('Your account must be assigned to a campus before creating activities.', 'error')
            return render_template('coordinator/create_act_scrn1.html', campuses=campuses)
        if not title or not description or not date_str:
            flash('Title, description, and date are required.', 'error')
            return render_template('coordinator/create_act_scrn1.html', campuses=campuses)
        if slots < 1 or slots > max_slots:
            flash(f'Volunteer slots must be between 1 and {max_slots}.', 'error')
            return render_template('coordinator/create_act_scrn1.html',
                                   campuses=campuses, max_slots=max_slots)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')
            return render_template('coordinator/create_act_scrn1.html', campuses=campuses)
        try:
            cover = _save_event_cover(request.files.get('cover_image'))
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('coordinator/create_act_scrn1.html',
                                   campuses=campuses, max_slots=max_slots)
        event = Event(title=title, description=description, date=date,
                      category=category, location=location,
                      required_skills=required_skills, slots=slots,
                      campus_id=campus_id,
                      cover_image_path=cover['path'] if cover else None,
                      cover_image_name=cover['original_name'] if cover else None)
        db.session.add(event)
        db.session.commit()
        flash('Activity created successfully!', 'success')
        return redirect(url_for('coordinator.coordinator_dash'))
    return render_template('coordinator/create_act_scrn1.html', campuses=campuses,
                           max_slots=_max_event_slots())


@coordinator_bp.route('/coordinator/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def edit_activity(event_id):
    """Edit an activity owned by the coordinator's assigned campus.

    Campus ownership is enforced server-side: the event must belong to the
    coordinator's campus, otherwise 403. The campus is never changed by the
    edit (a submitted campus_id is ignored), so a coordinator cannot move an
    event to another campus. Capacity cannot be reduced below the number of
    existing registrations.
    """
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.campus_id != current_user.campus_id:
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        date_str = request.form.get('date', '').strip()
        location = request.form.get('location', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        category = request.form.get('category', 'General').strip()
        slots = request.form.get('slots', 0, type=int)
        max_slots = _max_event_slots()

        if not title or not description or not date_str:
            flash('Title, description, and date are required.', 'error')
            return render_template('coordinator/edit_activity.html', event=event)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')
            return render_template('coordinator/edit_activity.html', event=event)
        if slots < 1 or slots > max_slots:
            flash(f'Volunteer slots must be between 1 and {max_slots}.', 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   max_slots=max_slots)

        # Registration-sensitive: do not reduce capacity below existing
        # registrations (PSU + external). This preserves all participation.
        existing = Registration.query.filter_by(event_id=event.id).count()
        if slots < existing:
            flash(f'Cannot reduce slots below existing registrations ({existing}).',
                  'error')
            return render_template('coordinator/edit_activity.html', event=event)

        event.title = title
        event.description = description
        event.date = date
        event.location = location
        event.category = category
        event.required_skills = required_skills
        event.slots = slots
        old_cover = event.cover_image_path
        try:
            cover = _save_event_cover(request.files.get('cover_image'))
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   max_slots=max_slots)
        if cover:
            event.cover_image_path = cover['path']
            event.cover_image_name = cover['original_name']
        # campus_id is intentionally left unchanged (server-side ownership).
        db.session.commit()
        if cover and old_cover:
            old_path = os.path.join(current_app.static_folder, old_cover)
            if os.path.isfile(old_path):
                os.remove(old_path)
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('coordinator.coordinator_dash'))

    return render_template('coordinator/edit_activity.html', event=event,
                           max_slots=_max_event_slots())


@coordinator_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def attendance():
    events = Event.query.filter_by(
        campus_id=current_user.campus_id).order_by(Event.date.desc()).all()
    selected_event_id = request.args.get('event_id', type=int)
    registrations = []
    if selected_event_id:
        selected_event = Event.query.filter_by(
            id=selected_event_id, campus_id=current_user.campus_id).first()
        if selected_event is None:
            abort(403)
        registrations = Registration.query.filter(
            Registration.event_id == selected_event.id,
            Registration.status != 'cancelled',
        ).all()
    if request.method == 'POST':
        event_id = request.form.get('event_id', type=int)
        reg_ids = request.form.getlist('registration_id')
        statuses = request.form.getlist('status')
        hours_list = request.form.getlist('hours_completed')
        selected_event = Event.query.filter_by(
            id=event_id, campus_id=current_user.campus_id).first()
        if selected_event is None:
            abort(403)
        try:
            registration_ids = [int(value) for value in reg_ids]
        except (TypeError, ValueError):
            abort(400)
        if len(registration_ids) != len(set(registration_ids)):
            abort(400)
        registrations_by_id = {
            registration.id: registration
            for registration in Registration.query.filter(
                Registration.id.in_(registration_ids or [-1]),
                Registration.event_id == selected_event.id,
            ).all()
        }
        if len(registrations_by_id) != len(registration_ids):
            abort(403)
        for i, reg_id in enumerate(reg_ids):
            reg = registrations_by_id[int(reg_id)]
            status = statuses[i] if i < len(statuses) else 'present'
            if status not in {'present', 'absent', 'excused'}:
                abort(400)
            try:
                hour_val = float(hours_list[i]) if i < len(hours_list) else 0.0
            except (TypeError, ValueError):
                abort(400)
            if hour_val < 0:
                abort(400)
            reg.status = (
                'completed' if status == 'present' and hour_val > 0
                else 'confirmed'
            )
            existing = Attendance.query.filter_by(
                registration_id=reg.id).first()
            if existing:
                existing.status = status
                existing.hours_completed = hour_val
            else:
                db.session.add(Attendance(registration_id=reg.id, user_id=reg.user_id,
                               event_id=reg.event_id, status=status, hours_completed=hour_val))
        db.session.commit()
        flash('Attendance updated successfully!', 'success')
        return redirect(url_for('coordinator.attendance', event_id=event_id))
    return render_template('coordinator/attendance_MnGmt.html', events=events, registrations=registrations)


@coordinator_bp.route('/events/<int:event_id>/milestones', methods=['POST'])
@login_required
@role_required('coordinator')
def upload_milestone(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.campus_id != current_user.campus_id:
        abort(403)
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('coordinator.coordinator_dash'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('coordinator.coordinator_dash'))
    category = request.form.get('category', 'photo')
    upload_dir = os.path.join(current_app.root_path,
                              'static', 'uploads', 'milestones')
    os.makedirs(upload_dir, exist_ok=True)
    ext = file.filename.rsplit(
        '.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in current_app.config.get('ALLOWED_EXTENSIONS', set()):
        flash('Unsupported file type.', 'error')
        return redirect(url_for('coordinator.coordinator_dash'))
    filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    milestone = Milestone(event_id=event.id, filename=file.filename,
                          upload_path=f'uploads/milestones/{filename}', category=category)
    db.session.add(milestone)
    db.session.commit()
    flash('Milestone uploaded successfully!', 'success')
    return redirect(url_for('coordinator.coordinator_dash'))


@coordinator_bp.route('/reports/events.csv')
@login_required
@role_required('coordinator')
def export_events_csv():
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    category = request.args.get('category', '').strip()
    try:
        rows, summary = build_events_report(
            campus_id=_coordinator_campus_id(), start_date=start_date,
            end_date=end_date, category=category)
    except ReportError:
        abort(400)
    campus_name = current_user.campus.name if current_user.campus else 'Campus'
    meta = {
        'title': f'{campus_name} Campus Activity Report',
        'scope': f'{campus_name} Campus (Coordinator)',
        'date_range': _date_range_label(start_date, end_date),
        'category': category or 'All Categories',
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'role_label': 'Coordinator',
    }
    csv_data = render_csv(rows, summary, meta)
    return Response(csv_data, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment;filename=campus_events.csv'})


@coordinator_bp.route('/reports/events.pdf')
@login_required
@role_required('coordinator')
def export_events_pdf():
    from app.reports import _build_meta
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    category = request.args.get('category', '').strip()
    try:
        rows, summary = build_events_report(
            campus_id=_coordinator_campus_id(), start_date=start_date,
            end_date=end_date, category=category)
    except ReportError:
        abort(400)
    campus_name = current_user.campus.name if current_user.campus else 'Campus'
    meta = _build_meta(
        title=f'{campus_name} Campus Activity Report',
        scope=f'{campus_name} Campus (Coordinator)',
        start_date=start_date, end_date=end_date, category=category,
        role_label='Coordinator')
    pdf_data = render_pdf(rows, summary, meta)
    return Response(pdf_data, mimetype='application/pdf', headers={
        'Content-Disposition': 'attachment;filename=campus_events.pdf'})


def _date_range_label(start_date, end_date):
    from app.reports import _date_range_label as _lbl
    return _lbl(start_date, end_date)


@coordinator_bp.route('/coordinator_analytics')
@login_required
@role_required('coordinator')
def analytics():
    # All aggregations scoped to the coordinator's own campus so the page
    # reflects the coordinator's reality, not the whole university.
    campus_name = current_user.campus.name if current_user.campus else 'Campus'
    kpi_cards = AnalyticsAggregator.kpi_summary(campus_id=current_user.campus_id)
    campus_data = AnalyticsAggregator.campus_stats()
    demographics = AnalyticsAggregator.role_demographics()
    trend_data = AnalyticsAggregator.trend_data(campus_id=current_user.campus_id)
    heatmap_data = AnalyticsAggregator.heatmap_data()
    forecast_data = AnalyticsAggregator.forecast_turnout(
        campus_id=current_user.campus_id)
    attendance_summary = AnalyticsAggregator.attendance_summary(
        campus_id=current_user.campus_id)
    categories = [row[0] for row in db.session.query(Event.category).filter(
        Event.campus_id == current_user.campus_id,
        Event.category.isnot(None)).distinct().order_by(Event.category).all()]

    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    category = request.args.get('category', '').strip()
    report_rows, report_summary = build_events_report(
        campus_id=_coordinator_campus_id(), start_date=start_date,
        end_date=end_date, category=category)

    # Phase 18: campus-scoped descriptive analytics (no cross-campus leakage).
    participation = AnalyticsAggregator.participation_summary(
        campus_id=_coordinator_campus_id(), start_date=start_date,
        end_date=end_date, category=category)
    category_breakdown = AnalyticsAggregator.category_distribution(
        campus_id=_coordinator_campus_id(), start_date=start_date,
        end_date=end_date)
    activity_breakdown = AnalyticsAggregator.activity_performance(
        campus_id=_coordinator_campus_id(), start_date=start_date,
        end_date=end_date, category=category)
    monthly = AnalyticsAggregator.monthly_engagement(
        campus_id=_coordinator_campus_id())
    weekly = AnalyticsAggregator.weekly_engagement(
        campus_id=_coordinator_campus_id())
    type_split = AnalyticsAggregator.psu_vs_outsider(
        campus_id=_coordinator_campus_id(), start_date=start_date,
        end_date=end_date, category=category)

    return render_template('coordinator/coordinator_analytics.html',
                            campus_name=campus_name,
                            kpi_cards=kpi_cards,
                            campus_data=campus_data,
                            demographics=demographics,
                            trend_data=trend_data,
                            heatmap_data=heatmap_data,
                            forecast_data=forecast_data,
                            attendance_summary=attendance_summary,
                            categories=categories,
                            report_rows=report_rows,
                            report_summary=report_summary,
                            participation=participation,
                            category_breakdown=category_breakdown,
                            activity_breakdown=activity_breakdown,
                            monthly=monthly,
                            weekly=weekly,
                            type_split=type_split)


# ── Outsider (External Volunteer) manual encoding ───────────────────────────────

@coordinator_bp.route('/coordinator/events/<int:event_id>/external', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def add_external_participant(event_id):
    """Coordinators manually encode an outsider for one of their campus events."""
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.campus_id != current_user.campus_id:
        abort(403)

    if request.method == 'POST':
        id_number = request.form.get('id_number', '').strip()
        if not id_number:
            flash('ID number is required for outsider registration.', 'error')
            return render_template(
                'coordinator/add_external.html', event=event), 400
        from app.models.event import Registration
        from app.routes.events import _upsert_external_participant
        participant = _upsert_external_participant(
            id_number,
            name=request.form.get('name', '').strip(),
            contact_number=request.form.get('contact_number', '').strip(),
            address=request.form.get('address', '').strip(),
            email=request.form.get('email', '').strip())
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
                    f'was added to "{event.title}" by a coordinator.',
            notification_type='external_registration',
            related_event_id=event.id)
    flash('External volunteer added to the activity.', 'success')
    return redirect(url_for('coordinator.attendance', event_id=event.id))

    return render_template('coordinator/add_external.html', event=event)
