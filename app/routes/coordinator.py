"""
Coordinator Routes for PSU Volunteer Hub
==========================================
Manages event creation, attendance tracking, and coordinator dashboard.
"""
import os
import uuid
import zipfile
from calendar import Calendar
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response, abort, send_from_directory
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import insert, update, case, or_
from app.pagination import paginate, report_page
from app.models import db
from app.models.event import (ActivityCategory, Event, EventAnnouncement,
                              Registration, Attendance, Campus, Milestone,
                              CancellationRequest, SdgGoal, capacity_query, ExternalParticipant)
from app.utils.decorators import role_required, roles_required
from app.models.notification import Notification, notify_campus_coordinators
from app.models.notification import notify
from app.utils.audit import log_activity
from app.models.user import SystemSetting, User, Skill
from app.recommendation.analytics import AnalyticsAggregator
from app.dashboard import summarize_report, resolve_period, dashboard_evidence, consolidate_attention, annual_plan_summary
from app.reports import (
    build_events_report, batched_events_report, render_csv, render_pdf, ReportError, parse_date_range)
from datetime import datetime, timedelta
from app.services.activity_workflow import attendance_open, local_now

coordinator_bp = Blueprint('coordinator', __name__, url_prefix='')

EVENT_COVER_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
EVENT_COVER_MAX_BYTES = 5 * 1024 * 1024
MILESTONE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'pdf', 'docx'}


def _max_event_slots():
    """Read configured slot ceiling, clamp to at least one; default to 100 if invalid."""
    setting = SystemSetting.query.filter_by(key='max_slots_per_event').first()
    try:
        return max(1, int(setting.value)) if setting else 100
    except (TypeError, ValueError):
        return 100


def _activity_categories():
    """Return valid categories even while a fresh database is being seeded.

    The configured category list is the application-level source of truth. The
    database table lets administrators extend it, but an empty lookup table
    must not prevent coordinators from creating or editing activities.
    """
    configured = current_app.config.get('EVENT_CATEGORIES', [])
    stored = [
        category.name
        for category in ActivityCategory.query.order_by(
            ActivityCategory.name,
        ).all()
    ]
    return list(dict.fromkeys([*configured, *stored, 'General']))


def _selected_sdgs(form):
    """Resolve numeric submitted SDG IDs against stored catalogue, ordered by number.

    Ignore nonnumeric/unknown IDs; create/edit routes require at least one
    resolved selection when catalogue exists.
    """
    ids = [int(value) for value in form.getlist('sdg_ids') if value.isdigit()]
    return SdgGoal.query.filter(SdgGoal.id.in_(ids)).order_by(SdgGoal.number).all() if ids else []


def _activity_form_context(**context):
    """Supply category/SDG choices and slot ceiling without replacing caller overrides."""
    context.setdefault('categories', _activity_categories())
    context.setdefault('skill_choices', Skill.query.order_by(Skill.name).all())
    context.setdefault('sdgs', SdgGoal.query.order_by(SdgGoal.number).all())
    context.setdefault('max_slots', _max_event_slots())
    return context


def _attendance_state(event, now):
    if event.end_date is None:
        return {'kind': 'locked', 'label': 'End time not recorded · read-only', 'time': event.date}
    if event.lifecycle_status == 'cancelled':
        return {'kind': 'locked', 'label': 'Activity cancelled · read-only', 'time': event.date}
    if now < event.date:
        return {'kind': 'locked', 'label': 'Attendance opens at activity start', 'time': event.date}
    if now >= event.end_date:
        return {'kind': 'closed', 'label': 'Attendance locked', 'time': event.end_date}
    return {'kind': 'active', 'label': 'Attendance open', 'time': event.end_date}


def _save_event_cover(file):
    """Validate cover extension, real image format, and 5 MB limit before saving.

    Store UUID filename under public event uploads; keep sanitized original
    name as metadata. Return relative path, or None for no file. This saves
    disk content only; caller separately saves event reference in database.
    """
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


def _validate_milestone(file):
    """Validate milestone size/type before private storage; rewind stream after checks.

    Images must decode and match extension. PDF check verifies %PDF- prefix;
    DOCX check verifies ZIP structure only, not full document contents.
    These format checks are not malware scanning. Return allowed extension.
    """
    extension = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
    if extension not in MILESTONE_EXTENSIONS:
        raise ValueError('Milestones must be JPEG, PNG, WebP, PDF, or DOCX files.')
    file.stream.seek(0, os.SEEK_END)
    if file.stream.tell() > current_app.config['MILESTONE_MAX_BYTES']:
        raise ValueError('Milestone files must be 10 MB or smaller.')
    file.stream.seek(0)
    if extension in {'jpg', 'jpeg', 'png', 'webp'}:
        try:
            with Image.open(file.stream) as image:
                detected = (image.format or '').lower()
                image.verify()
        except (UnidentifiedImageError, OSError):
            raise ValueError('Milestone image is not valid.')
        allowed_extensions = {'jpg', 'jpeg'} if detected == 'jpeg' else {detected}
        if extension not in allowed_extensions:
            raise ValueError('Milestone filename does not match its image content.')
    elif extension == 'pdf' and not file.stream.read(5).startswith(b'%PDF-'):
        raise ValueError('Milestone file is not a valid PDF.')
    elif extension == 'docx' and not zipfile.is_zipfile(file.stream):
        raise ValueError('Milestone file is not a valid DOCX.')
    file.stream.seek(0)
    return extension


def _coordinator_campus_id():
    """Coordinator campus scope is always derived server-side, never from the
    request, so a forged ?campus_id= parameter cannot leak another campus."""
    campus_id = current_user.campus_id
    if not campus_id:
        abort(403)
    return campus_id


def _parse_event_schedule(form):
    """Parse start/optional end and derive cancellation deadline from whole days.

    Accept 0-365 days before start, default 2. End must follow start when
    supplied. Return (schedule, None) or (None, error); caller displays errors
    before writes. Start must be in the future and an end time is required.
    """
    try:
        start = datetime.fromisoformat(form.get('date', '').strip())
        end_raw = form.get('end_date', '').strip()
        end = datetime.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        return None, 'Enter valid activity dates and times.'
    days_raw = form.get('cancellation_days', '2').strip()
    try:
        cancellation_days = int(days_raw)
    except ValueError:
        return None, 'Enter whole days before the activity for cancellations.'
    if not 0 <= cancellation_days <= 365:
        return None, 'Cancellation must close from 0 to 365 days before the activity.'
    deadline = start - timedelta(days=cancellation_days)
    if start.tzinfo or (end and end.tzinfo):
        return None, 'Use Philippine local time without a timezone suffix.'
    if start <= local_now() or end is None:
        return None, 'A future start and an end date/time are required.'
    if end and end <= start:
        return None, 'The end date and time must be after the start.'
    return (start, end, deadline), None


def _campus_calendar(campus_id, year=None, month=None, dashboard=False):
    """Group campus activities by start day in selected calendar month.

    Calendar scope is independent of performance-period selector. Invalid
    year/month falls back to current month; stop navigation at supported year
    limits. Dashboard links preserve query state and point to calendar anchor.
    """
    now = local_now()
    year, month = year or now.year, month or now.month
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        year, month = now.year, now.month
    end = datetime.max if (year, month) == (9999, 12) else (
        datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1))
    events = Event.query.filter_by(campus_id=campus_id).filter(
        Event.date >= datetime(year, month, 1), Event.date <= end if end == datetime.max else Event.date < end
    ).order_by(Event.date, Event.id).all()
    by_day = {}
    for event in events:
        by_day.setdefault(event.date.day, []).append(event)
    previous = ((year - 1, 12) if month == 1 else (year, month - 1)) if (year, month) != (1, 1) else None
    following = ((year + 1, 1) if month == 12 else (year, month + 1)) if (year, month) != (9999, 12) else None

    def month_url(value):
        """Build internal previous/next month link, or None at calendar boundary."""
        if value is None:
            return None
        query = request.args.to_dict(flat=False) if dashboard else {}
        query.update({'calendar_year' if dashboard else 'year': value[0],
                      'calendar_month' if dashboard else 'month': value[1]})
        if dashboard:
            query['_anchor'] = 'activity-calendar'
        return url_for('coordinator.coordinator_dash' if dashboard else 'coordinator.activity_calendar', **query)

    return dict(calendar_weeks=Calendar(firstweekday=0).monthdayscalendar(year, month),
                calendar_events=by_day, calendar_month=datetime(year, month, 1).strftime('%B %Y'),
                calendar_year=year, calendar_number=month,
                previous_calendar_url=month_url(previous), next_calendar_url=month_url(following))


@coordinator_bp.route('/coordinator_dash')
@login_required
@role_required('coordinator')
def coordinator_dash():
    from app.services.workspace_reports import legacy_report_url
    return redirect(legacy_report_url(dashboard=True))


@coordinator_bp.route('/coordinator/calendar')
@login_required
@role_required('coordinator')
def activity_calendar():
    """Render assigned-campus calendar through shared month-boundary rules."""
    return render_template('coordinator/activity_calendar.html',
                           **_campus_calendar(_coordinator_campus_id(),
                                              request.args.get('year', type=int),
                                              request.args.get('month', type=int)))


@coordinator_bp.route('/coordinator/cancellation-requests', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def cancellation_requests():
    return redirect(url_for("workspace.activities"))


@coordinator_bp.route('/create_activity', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def create_activity():
    return redirect(url_for("workspace.create_activity", step=1))


@coordinator_bp.route('/coordinator/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def edit_activity(event_id):
    """Edit only activity matching signed-in user's campus; campus stays unchanged.

    Revalidate category, SDGs, dates, slots and targets before
    saving. Capacity cannot fall below count of all existing registrations,
    including cancelled rows; this differs from join route's occupied-slot rule.
    Save new cover reference, commit, then remove replaced cover from disk.
    Ownership check is server-side; submitted campus_id cannot move activity.
    """
    event = Event.query.filter_by(id=event_id).with_for_update().first()
    if event is None:
        abort(404)
    if event.campus_id != current_user.campus_id:
        abort(403)

    if event.lifecycle_status != 'approved' or event.date <= local_now():
        abort(409, description='Started or cancelled activities cannot be edited.')

    categories = _activity_categories()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        date_str = request.form.get('date', '').strip()
        location = request.form.get('location', '').strip()
        available_skills = {skill.name: skill for skill in Skill.query.all()}
        if not set(request.form.getlist('required_skills')) <= available_skills.keys():
            flash('Select available skills from the list.', 'error')
            return render_template('coordinator/edit_activity.html', event=event, **_activity_form_context())
        category = request.form.get('category', 'General').strip()
        slots = request.form.get('slots', 0, type=int)
        target_participants = request.form.get('target_participants', type=int)
        max_slots = _max_event_slots()

        if category not in categories:
            flash('Select a valid activity category.', 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   **_activity_form_context())
        sdgs = _selected_sdgs(request.form)
        if len(sdgs) != len(set(request.form.getlist('sdg_ids'))):
            flash('Select available Sustainable Development Goals from the list.', 'error')
            return render_template('coordinator/edit_activity.html', event=event, **_activity_form_context())
        if SdgGoal.query.count() and not sdgs:
            flash('Select at least one Sustainable Development Goal.', 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   **_activity_form_context())
        if not title or not description or not date_str:
            flash('Title, description, and date are required.', 'error')
            return render_template('coordinator/edit_activity.html', event=event, **_activity_form_context())
        schedule, error = _parse_event_schedule(request.form)
        if error:
            flash(error, 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   **_activity_form_context())
        date, end_date, cancellation_deadline = schedule
        if slots < 1 or slots > max_slots:
            flash(f'Volunteer slots must be between 1 and {max_slots}.', 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   **_activity_form_context())
        if target_participants is not None and target_participants < 1:
            flash('Target participants must be a positive number when provided.', 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   **_activity_form_context())

        # Registration-sensitive: do not reduce capacity below existing
        # registrations (PSU + external). This preserves all participation.
        existing = Registration.query.filter_by(event_id=event.id).count()
        if slots < existing:
            flash(f'Cannot reduce slots below existing registrations ({existing}).',
                  'error')
            return render_template('coordinator/edit_activity.html', event=event, **_activity_form_context())

        event.title = title
        event.description = description
        event.date = date
        event.end_date = end_date
        event.cancellation_deadline = cancellation_deadline
        event.location = location
        event.category = category
        event.required_skills_rel = [available_skills[name] for name in dict.fromkeys(request.form.getlist('required_skills'))]
        event.sdgs = sdgs
        event.slots = slots
        event.target_participants = target_participants
        old_cover = event.cover_image_path
        try:
            cover = _save_event_cover(request.files.get('cover_image'))
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('coordinator/edit_activity.html', event=event,
                                   **_activity_form_context())
        if cover:
            event.cover_image_path = cover['path']
            event.cover_image_name = cover['original_name']
            event.cover_uploaded_by_id = current_user.id
            event.cover_uploaded_at = datetime.utcnow()
        # campus_id is intentionally left unchanged (server-side ownership).
        db.session.commit()
        if cover and old_cover:
            old_path = os.path.join(current_app.static_folder, old_cover)
            if os.path.isfile(old_path):
                os.remove(old_path)
        flash('Activity updated successfully!', 'success')
        return redirect(url_for('workspace.activity',event_id=event.id))

    return render_template('coordinator/edit_activity.html', event=event,
                           **_activity_form_context())


@coordinator_bp.route('/coordinator/events/<int:event_id>/delete', methods=['POST'])
@login_required
@role_required('coordinator')
def delete_activity(event_id):
    abort(405, description="Activities are preserved. Cancel an activity with a reason instead.")


@coordinator_bp.route('/coordinator/events/<int:event_id>/announcements',
                      methods=['POST'])
@login_required
@role_required('coordinator')
def publish_announcement(event_id):
    """Save typed campus-owned activity announcement and notify pending/confirmed users.

    Require allowed type and 1-1000 characters. Save announcement/notifications
    in one transaction; external and completed/cancelled signups are not notified.
    Cancelled/postponed announcement type does not itself change event/signups.
    """
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.campus_id != current_user.campus_id:
        abort(403)
    announcement_type = request.form.get('announcement_type', '').strip()
    message = request.form.get('message', '').strip()
    allowed = {'last_call', 'event_update', 'cancelled_postponed'}
    if announcement_type not in allowed or not message:
        flash('Select an announcement type and enter a message.', 'error')
        return redirect(url_for('workspace.activity_documents',event_id=event.id))
    if len(message) > 1000:
        flash('Announcement must be 1,000 characters or fewer.', 'error')
        return redirect(url_for('workspace.activity_documents',event_id=event.id))

    db.session.add(EventAnnouncement(
        event_id=event.id,
        author_id=current_user.id,
        announcement_type=announcement_type,
        message=message,
    ))
    registrations = Registration.query.filter(
        Registration.event_id == event.id,
        Registration.user_id.isnot(None),
        Registration.status.in_(('pending', 'confirmed')),
    ).all()
    for registration in registrations:
        db.session.add(Notification(
            user_id=registration.user_id,
            title=f'Activity update: {event.title}',
            message=message,
            notification_type=announcement_type,
            related_event_id=event.id,
        ))
    db.session.commit()
    flash(f'Announcement published to {len(registrations)} volunteer(s).',
          'success')
    return redirect(url_for('workspace.activity_documents',event_id=event.id))


@coordinator_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def attendance():
    """Search/page campus roster and save only submitted attendance choices.

    GET excludes cancelled signups, supports PSU/external name/email/ID search
    and status filter, and shows 15 rows per page. Display counts describe
    current page, not entire activity. Activity picker shows up to 25 matches.

    POST locks campus event and submitted eligible registrations; reject
    duplicate IDs, foreign IDs, invalid statuses, or batches above 50. Check-in
    opens 30 minutes before start. Blank status leaves row unchanged.
    Present becomes completed only after end; otherwise signup is confirmed.
    Saving early present does not auto-complete later: final attendance must
    be saved after end for completion/certificate eligibility.
    Bulk update existing rows, insert missing attendance, then commit together.
    """
    now = local_now()
    volunteer_search = request.args.get('volunteer_search', '').strip()
    attendance_filter = request.args.get('attendance_status', '')
    if attendance_filter not in ('', 'present', 'absent', 'excused', 'unmarked'):
        attendance_filter = ''
    campus_events = Event.query.filter_by(campus_id=current_user.campus_id)
    search = request.args.get('activity_search', '').strip()
    choices = campus_events
    if search:
        choices = choices.filter(Event.title.icontains(search, autoescape=True))
    events = choices.order_by(Event.date.desc(), Event.id.desc()).limit(25).all() if request.method == 'GET' else []
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    today_events = campus_events.filter(Event.date >= tomorrow - timedelta(days=1), Event.date < tomorrow).order_by(Event.date, Event.id).limit(6).all() if request.method == 'GET' else []
    future_events = campus_events.filter(Event.date >= tomorrow).order_by(Event.date, Event.id).limit(3).all() if request.method == 'GET' else []
    quick_activities = [
        {'event': event, 'state': _attendance_state(event, now)}
        for event in [*today_events, *future_events]
    ]
    selected_event_id = request.args.get('event_id', type=int)
    selected_event = None
    registrations = []
    pagination = None
    if selected_event_id and request.method == 'GET':
        selected_event = Event.query.filter_by(
            id=selected_event_id, campus_id=current_user.campus_id).first()
        if selected_event is None:
            abort(403)
        if selected_event not in events:
            events.append(selected_event)
        roster = Registration.query.filter(
            Registration.event_id == selected_event.id,
            Registration.user_id.isnot(None),
            Registration.status != 'cancelled',
        )
        if volunteer_search:
            roster = roster.filter(or_(
                Registration.user.has(or_(
                    User.name.icontains(volunteer_search, autoescape=True),
                    User.email.icontains(volunteer_search, autoescape=True),
                    User.id_number.icontains(volunteer_search, autoescape=True))),
                Registration.external_participant.has(or_(
                    ExternalParticipant.name.icontains(volunteer_search, autoescape=True),
                    ExternalParticipant.email.icontains(volunteer_search, autoescape=True),
                    ExternalParticipant.id_number.icontains(volunteer_search, autoescape=True))),
            ))
        if attendance_filter == 'unmarked':
            roster = roster.filter(~Registration.attendance_record.has())
        elif attendance_filter:
            roster = roster.filter(Registration.attendance_record.has(Attendance.status == attendance_filter))
        pagination = paginate(roster.join(User, User.id == Registration.user_id).options(
            joinedload(Registration.user), joinedload(Registration.external_participant),
            joinedload(Registration.attendance_record)).order_by(User.name, Registration.id), per_page=15)
        registrations = pagination.items
    if request.method == 'POST':
        event_id = request.form.get('event_id', type=int)
        reg_ids = request.form.getlist('registration_id')
        statuses = request.form.getlist('status')
        if len(reg_ids) > 50:
            abort(400)
        selected_event = Event.query.filter_by(
            id=event_id, campus_id=current_user.campus_id).populate_existing().with_for_update().first()
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
                Registration.status != 'cancelled',
            ).options(joinedload(Registration.attendance_record)).populate_existing().with_for_update().all()
        }
        if len(registrations_by_id) != len(registration_ids):
            abort(403)
        now = local_now()
        if not attendance_open(selected_event, now):
            flash('Attendance is editable only while the activity is ongoing. Ended or unscheduled activities are read-only.', 'error')
            return redirect(url_for('coordinator.attendance', event_id=selected_event.id))
        activity_ended = now >= (selected_event.end_date or selected_event.date)
        registration_updates, attendance_updates, attendance_inserts = [], [], []
        for i, reg_id in enumerate(reg_ids):
            reg = registrations_by_id[int(reg_id)]
            status = statuses[i] if i < len(statuses) else ''
            if not status:
                continue
            if status not in {'present', 'absent', 'excused'}:
                abort(400)
            registration_updates.append(dict(id=reg.id, status='confirmed'))
            existing = reg.attendance_record
            if existing:
                attendance_updates.append(dict(id=existing.id, status=status))
            else:
                attendance_inserts.append(dict(registration_id=reg.id, user_id=reg.user_id,
                                              event_id=reg.event_id, status=status))
        for model, changes in ((Registration, registration_updates), (Attendance, attendance_updates)):
            if changes:
                values = {change['id']: change['status'] for change in changes}
                db.session.execute(update(model).where(model.id.in_(list(values))).values(
                    status=case(values, value=model.id)), execution_options={'synchronize_session': False})
        if attendance_inserts:
            db.session.execute(insert(Attendance).values(attendance_inserts))
        if not attendance_open(selected_event):
            db.session.rollback()
            abort(409, description='The activity ended before attendance was saved.')
        db.session.commit()
        flash('Attendance saved. Recorded presence confirms participation when the activity ends.', 'success')
        return redirect(url_for('coordinator.attendance', event_id=event_id,
                                volunteer_search=volunteer_search, attendance_status=attendance_filter,
                                activity_search=search,
                                page=request.args.get('page', 1, type=int)))
    attendance_opens_at = selected_event.date if selected_event else None
    attendance_counts = {'registered': len(registrations), 'present': 0,
                         'absent': 0, 'excused': 0, 'unmarked': 0}
    for registration in registrations:
        status = registration.attendance_record.status if registration.attendance_record else 'unmarked'
        attendance_counts[status] += 1
    return render_template('workspace/attendance.html', events=events, now=now,
                           pagination=pagination, activity_search=search,
                           volunteer_search=volunteer_search, attendance_filter=attendance_filter,
                           registrations=registrations, selected_event=selected_event,
                           quick_activities=quick_activities,
                           attendance_state=(_attendance_state(selected_event, now)
                                             if selected_event else None),
                           attendance_counts=attendance_counts,
                           attendance_opens_at=attendance_opens_at,
                           attendance_locked=bool(selected_event and not attendance_open(selected_event, now)),
                           activity_ended=bool(selected_event and now >= (selected_event.end_date or selected_event.date)))


@coordinator_bp.route('/events/<int:event_id>/milestones', methods=['POST'])
@login_required
@role_required('coordinator')
def upload_milestone(event_id):
    """Validate and store owned activity evidence under private UUID file path.

    Keep sanitized original filename in database for download. File save
    precedes database commit; validation and private download checks are separate.
    """
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.campus_id != current_user.campus_id:
        abort(403)
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('workspace.activity_documents',event_id=event.id))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('workspace.activity_documents',event_id=event.id))
    category = request.form.get('category', 'photo')
    try:
        ext = _validate_milestone(file)
    except ValueError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('workspace.activity_documents',event_id=event.id))
    upload_dir = os.path.join(current_app.config['PRIVATE_UPLOAD_FOLDER'], 'milestones')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    milestone = Milestone(
        event_id=event.id,
        filename=secure_filename(file.filename),
        upload_path=f'milestones/{filename}',
        category=category,
        uploaded_by_id=current_user.id,
    )
    db.session.add(milestone)
    db.session.commit()
    flash('Milestone uploaded successfully!', 'success')
    return redirect(url_for('workspace.activity_documents',event_id=event.id))


@coordinator_bp.route('/milestones/<int:milestone_id>/download')
@login_required
@roles_required('coordinator', 'director', 'admin')
def download_milestone(milestone_id):
    """Download private milestone for permitted internal role and campus scope.

    Coordinators must own event campus; director/admin can read across campuses.
    Retired uploads/ paths return 410. Serve attachment from private folder,
    using original filename for download rather than exposing stored UUID path.
    """
    milestone = db.session.get(Milestone, milestone_id)
    if milestone is None:
        abort(404)
    if current_user.role == 'coordinator' and milestone.event.campus_id != current_user.campus_id:
        abort(403)
    if milestone.upload_path.startswith('uploads/'):
        abort(410)
    directory, filename = os.path.split(milestone.upload_path)
    return send_from_directory(
        os.path.join(current_app.config['PRIVATE_UPLOAD_FOLDER'], directory),
        filename, as_attachment=True, download_name=milestone.filename)


@coordinator_bp.route('/reports/events.csv')
@login_required
@role_required('coordinator')
def export_events_csv():
    """Export all filtered campus activity rows, independent of screen page.

    Derive campus from account, validate report period/attention scope, fetch
    batches, and pass unchanged rows/totals to shared CSV renderer. Default
    export period is all dates unless supplied dates/preset narrow it.
    """
    category = request.args.get('category', '').strip()
    try:
        export_period = resolve_period(dict(request.args, period=request.args.get('period', 'all')))
        start_date, end_date = export_period['start'], export_period['end']
        rows, summary = batched_events_report(
            campus_id=_coordinator_campus_id(), start_date=start_date,
            end_date=end_date, category=category,
            activity_name=request.args.get('activity_name', ''),
            attention=request.args.get('attention', ''), event_id=request.args.get('event_id'))
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
    meta['activity_name'] = request.args.get('activity_name', '').strip()
    if request.args.get('attention'):
        from app.dashboard import ATTENTION_LABELS
        meta['scope'] += ' / ' + ATTENTION_LABELS[request.args['attention']]
    csv_data = render_csv(rows, summary, meta)
    return Response(csv_data, mimetype='text/csv', headers={
        'Content-Disposition': 'attachment;filename=campus_events.csv'})


@coordinator_bp.route('/reports/events.pdf')
@login_required
@role_required('coordinator')
def export_events_pdf():
    """Export same campus-scoped report source as CSV, formatted as PDF.

    Preserve dates/category/title/attention/event filters and full totals;
    never accept requested campus as replacement for account campus.
    """
    from app.reports import _build_meta
    category = request.args.get('category', '').strip()
    try:
        export_period = resolve_period(dict(request.args, period=request.args.get('period', 'all')))
        start_date, end_date = export_period['start'], export_period['end']
        rows, summary = batched_events_report(
            campus_id=_coordinator_campus_id(), start_date=start_date,
            end_date=end_date, category=category,
            activity_name=request.args.get('activity_name', ''),
            attention=request.args.get('attention', ''), event_id=request.args.get('event_id'))
    except ReportError:
        abort(400)
    campus_name = current_user.campus.name if current_user.campus else 'Campus'
    meta = _build_meta(
        title=f'{campus_name} Campus Activity Report',
        scope=f'{campus_name} Campus (Coordinator)',
        start_date=start_date, end_date=end_date, category=category,
        role_label='Coordinator')
    meta['activity_name'] = request.args.get('activity_name', '').strip()
    if request.args.get('attention'):
        from app.dashboard import ATTENTION_LABELS
        meta['scope'] += ' / ' + ATTENTION_LABELS[request.args['attention']]
    pdf_data = render_pdf(rows, summary, meta)
    return Response(pdf_data, mimetype='application/pdf', headers={
        'Content-Disposition': 'attachment;filename=campus_events.pdf'})


def _date_range_label(start_date, end_date):
    """Reuse shared export date label so coordinator downloads use same wording."""
    from app.reports import _date_range_label as _lbl
    return _lbl(start_date, end_date)


@coordinator_bp.route('/coordinator_analytics')
@login_required
@role_required('coordinator')
def analytics():
    from app.services.workspace_reports import legacy_report_url
    return redirect(legacy_report_url())


# ── Outsider (External Volunteer) manual encoding ───────────────────────────────

@coordinator_bp.route('/coordinator/events/<int:event_id>/external', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def add_external_participant(event_id):
    if request.method == 'POST':
        abort(405, description='Use the named external roster in the activity workspace.')
    return redirect(url_for('workspace.external', event_id=event_id))
