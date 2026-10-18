"""
Events Routes for PSU Volunteer Hub
=====================================
Manages event listings, registrations, and the volunteer dashboard.
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort, current_app)
from flask_login import login_required, current_user
from email_validator import EmailNotValidError, validate_email
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func
from app.models import db
from app.models.user import AuthSecurityEvent, VolunteerProfile
from app.models.event import (Event, Registration, Attendance, Campus,
                             ExternalParticipant, CancellationRequest)
from app.models.policy import ParticipationAgreementRevision, PrivacyRevision
from app.recommendation.engine import get_recommendations, bootstrap_from_event
from app.services.email import send_email
from app.utils.decorators import role_required
from app.models.notification import notify, notify_campus_coordinators
from app.utils.audit import log_activity
from datetime import datetime, timedelta
from calendar import Calendar
import secrets

events_bp = Blueprint('events', __name__, url_prefix='')

CANCELLATION_REASONS = (
    'Medical / Health Reason', 'Family Emergency', 'Academic Conflict',
    'Work / Schedule Conflict', 'Transportation Problem',
    'Personal Emergency', 'Other',
)
EXTERNAL_REGISTRATION_LIMIT = 5
EXTERNAL_REGISTRATION_WINDOW = timedelta(hours=1)
EXTERNAL_LINK_MAX_AGE = 60 * 60 * 24 * 30


def _agreement_for(event):
    if event.participation_agreement_text:
        return {'title': 'Event Participation Agreement',
                'body': event.participation_agreement_text,
                'version': event.participation_agreement_version or 'event'}
    revision = ParticipationAgreementRevision.query.filter_by(
        is_active=True).order_by(ParticipationAgreementRevision.published_at.desc()).first()
    return ({'title': revision.title, 'body': revision.body, 'version': revision.version}
            if revision else {
                'title': 'Event Participation Agreement',
                'version': 'system-default',
                'body': ('By joining this activity, I commit to participate, follow PSU '
                         'guidelines, and submit a cancellation request if I cannot attend.'),
            })


def _privacy_for_external():
    """Return the notice a new guest must acknowledge."""
    revision = PrivacyRevision.query.filter_by(is_active=True).order_by(
        PrivacyRevision.published_at.desc()).first()
    if revision:
        return {
            'title': revision.title,
            'body': revision.body,
            'version': revision.version,
        }
    return {
        'title': 'Privacy Notice',
        'body': ('PSU Volunteer Hub uses your name, email, and optional phone '
                 'number to manage this activity registration and related '
                 'cancellation request.'),
        'version': 'system-default',
    }


def _external_registration_error(event):
    if event.date <= datetime.now():
        return 'This activity has already started and cannot accept registrations.'
    if event.slots <= 0 or event.slots_remaining() <= 0:
        return 'This activity no longer has available slots.'
    if _agreement_for(event) is None:
        return 'This activity cannot accept registrations until its agreement is published.'
    return None


def _external_throttle_key(_email=''):
    """Limit public guest submissions by source, not a user-controlled email."""
    ip_address = request.remote_addr or 'unknown'
    return AuthSecurityEvent.subject(f'external_registration|{ip_address}')


def _external_registration_is_limited(email):
    cutoff = datetime.utcnow() - EXTERNAL_REGISTRATION_WINDOW
    return AuthSecurityEvent.query.filter(
        AuthSecurityEvent.action == 'external_registration',
        AuthSecurityEvent.subject_hash == _external_throttle_key(email),
        AuthSecurityEvent.created_at >= cutoff,
    ).count() >= EXTERNAL_REGISTRATION_LIMIT


def _record_external_registration_attempt(email):
    db.session.add(AuthSecurityEvent(
        action='external_registration',
        subject_hash=_external_throttle_key(email),
    ))


def _external_reference():
    """Generate a non-guessable reference without exposing a database ID."""
    while True:
        reference = f'EXT-{secrets.token_hex(6).upper()}'
        if not ExternalParticipant.query.filter_by(id_number=reference).first():
            return reference


def _guest_external_participant(name, email, contact_number):
    """Find a guest by contact address or create a new guest record."""
    participant = ExternalParticipant.query.filter(
        func.lower(ExternalParticipant.email) == email.lower()).first()
    if participant is None:
        participant = ExternalParticipant(
            id_number=_external_reference(),
            name=name,
            email=email,
            contact_number=contact_number or None,
        )
        db.session.add(participant)
    else:
        # Preserve coordinator-entered data, but fill genuinely missing fields.
        if not participant.name:
            participant.name = name
        if not participant.contact_number and contact_number:
            participant.contact_number = contact_number
    db.session.flush()
    return participant


def _external_token(registration):
    serializer = URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'], salt='external-registration')
    return serializer.dumps({'registration_id': registration.id})


def _external_registration_from_token(token):
    serializer = URLSafeTimedSerializer(
        current_app.config['SECRET_KEY'], salt='external-registration')
    payload = serializer.loads(token, max_age=EXTERNAL_LINK_MAX_AGE)
    registration_id = payload.get('registration_id') if isinstance(payload, dict) else None
    registration = db.session.get(Registration, registration_id)
    if registration is None or not registration.is_external:
        raise BadSignature('Unknown external registration')
    return registration


def _send_external_confirmation(registration):
    participant = registration.external_participant
    if not participant or not participant.email:
        return
    manage_url = url_for(
        'events.external_registration_manage',
        token=_external_token(registration),
        _external=True,
    )
    body = (
        f'Hello {participant.name},\n\n'
        f'Your external volunteer registration for "{registration.event.title}" '
        'has been received. No PSU account was created.\n\n'
        f'Manage your registration or request cancellation: {manage_url}\n\n'
        'This link expires after 30 days. Contact the campus coordinator if '
        'you need help after it expires.'
    )
    try:
        send_email(participant.email, 'PSU Volunteer Hub registration details', body)
    except Exception:
        current_app.logger.exception(
            'Could not send external registration confirmation to %s',
            participant.email,
        )


def _external_cancellation_available(registration):
    event = registration.event
    return (
        registration.status in ('pending', 'confirmed')
        and registration.attendance_record is None
        and (event.cancellation_deadline or event.date) > datetime.now()
        and not (registration.cancellation_request
                 and registration.cancellation_request.status == 'pending')
    )


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
    campuses = Campus.query.order_by(func.lower(Campus.name), Campus.name, Campus.id).all()
    available_campuses = {campus.id for campus in campuses}
    raw_campuses = [value.strip() for value in request.args.getlist('campus') if value.strip()]
    requested_campuses = request.args.getlist('campus', type=int)
    selected_campuses = set(requested_campuses) & available_campuses
    campus_mode = request.args.get('campus_mode', 'include')
    filter_error = None
    if len(requested_campuses) != len(raw_campuses) or not set(requested_campuses) <= available_campuses:
        filter_error = 'Some campus choices are unavailable. Choose campuses from the list and apply filters again.'
    if campus_mode not in ('include', 'exclude'):
        filter_error = 'Choose whether to show only or exclude the selected campuses, then apply filters again.'
        campus_mode = 'include'
    category = request.args.get('category', type=str) or None
    search = request.args.get('search', type=str) or None
    query = Event.query.filter(Event.date >= datetime.now(), Event.slots > 0)
    if filter_error:
        query = query.filter(db.false())
    elif selected_campuses:
        if campus_mode == 'exclude':
            query = query.filter(db.or_(Event.campus_id.is_(None),
                                       Event.campus_id.notin_(selected_campuses)))
        else:
            query = query.filter(Event.campus_id.in_(selected_campuses))
    if category:
        query = query.filter(Event.category == category)
    if search:
        like = f'%{search}%'
        query = query.filter(Event.title.ilike(
            like) | Event.description.ilike(like))
    query = query.order_by(Event.date.asc(), Event.id.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items
    # Data-driven category filter: distinct categories actually in use,
    # so the dropdown never offers options that return zero results.
    categories = [row[0] for row in db.session.query(
        Event.category).distinct().order_by(Event.category).all() if row[0]]
    registered_event_ids = set()
    if current_user.is_authenticated and current_user.role == 'volunteer':
        registered_event_ids = {
            registration.event_id
            for registration in Registration.query.filter_by(
                user_id=current_user.id).all()
            if registration.status != 'cancelled'
        }
    return render_template('volunteer/Volunteer_opportunities.html',
                           events=events, campuses=campuses,
                           categories=categories,
                           current_page=pagination.page,
                           total_pages=pagination.pages,
                           total_count=pagination.total,
                           selected_campuses=sorted(selected_campuses),
                           campus_mode=campus_mode,
                           filter_error=filter_error,
                           selected_category=category,
                           selected_status='upcoming',
                           search_query=search,
                           registered_event_ids=registered_event_ids), 400 if filter_error else 200


@events_bp.route('/opportunities/register/<int:event_id>', methods=['GET', 'POST'])
@login_required
@role_required('volunteer')
def register_for_event(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.date <= datetime.now():
        flash('This activity has already started and cannot accept registrations.', 'error')
        return redirect(url_for('events.opportunities'))
    agreement = _agreement_for(event)
    if agreement is None:
        flash('This activity cannot accept registrations until its participation agreement is published.', 'error')
        return redirect(url_for('events.opportunities'))
    if request.method == 'GET':
        return render_template('events/registration_consent.html', event=event,
                               agreement=agreement, external=False)
    existing = Registration.query.filter_by(
        user_id=current_user.id, event_id=event_id).first()
    if existing and existing.status != 'cancelled':
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('events.opportunities'))
    if event.slots > 0 and event.slots_remaining() <= 0:
        flash('No available slots for this event.', 'error')
        return redirect(url_for('events.opportunities'))
    if request.form.get('accept_agreement') != 'yes' or (event.nda_required and request.form.get('accept_nda') != 'yes'):
        flash('Accept the required agreement(s) before joining.', 'error')
        return render_template('events/registration_consent.html', event=event,
                               agreement=agreement, external=False), 400
    if existing:
        existing.status = 'confirmed'
        existing.policy_accepted_at = datetime.utcnow()
        existing.policy_version = agreement['version']
        existing.nda_accepted_at = datetime.utcnow() if event.nda_required else None
        existing.nda_version = event.nda_version if event.nda_required else None
        registration = existing
        success_message = 'Your registration has been restored.'
    else:
        registration = Registration(user_id=current_user.id, event_id=event_id,
            status='confirmed', policy_accepted_at=datetime.utcnow(),
            policy_version=agreement['version'],
            nda_accepted_at=datetime.utcnow() if event.nda_required else None,
            nda_version=event.nda_version if event.nda_required else None)
        db.session.add(registration)
        success_message = 'Successfully registered for the event!'
    db.session.flush()
    log_activity('participation_agreement_accepted', registration,
                 {'event_id': event.id, 'version': agreement['version']})
    if event.nda_required:
        log_activity('nda_accepted', registration, {'event_id': event.id, 'version': event.nda_version})
    db.session.commit()
    bootstrap_from_event(current_user, event)
    notify_campus_coordinators(
        event.campus_id,
        title=f'New registration: {event.title}',
        message=f'{current_user.name or current_user.email} registered for '
                f'"{event.title}".',
        notification_type='registration',
        related_event_id=event.id)
    db.session.commit()
    flash(success_message, 'success')
    return redirect(url_for('events.opportunities'))


@events_bp.route('/registrations/<int:registration_id>/cancel', methods=['GET', 'POST'])
@login_required
@role_required('volunteer')
def cancel_registration(registration_id):
    """Request review of a future signup cancellation; never cancel directly."""
    registration = db.session.get(Registration, registration_id)
    if registration is None:
        abort(404)
    if registration.user_id != current_user.id:
        abort(403)
    event = registration.event
    if (registration.status not in ('pending', 'confirmed')
            or registration.attendance_record is not None
            or (event.cancellation_deadline or event.date) <= datetime.now()):
        flash('Cancellation is unavailable because the activity has started, attendance was recorded, or the deadline passed.', 'error')
        return redirect(url_for('events.volunteer_dash'))
    if registration.cancellation_request and registration.cancellation_request.status == 'pending':
        flash('A cancellation request is already awaiting coordinator review.', 'warning')
        return redirect(url_for('events.volunteer_dash'))
    if request.method == 'GET':
        return render_template('events/cancellation_request.html', registration=registration,
                               reasons=CANCELLATION_REASONS)
    reason = request.form.get('reason', '').strip()
    details = request.form.get('details', '').strip()
    if reason not in CANCELLATION_REASONS or (reason == 'Other' and not details):
        flash('Choose a cancellation reason. Explain Other reasons.', 'error')
        return render_template('events/cancellation_request.html', registration=registration,
                               reasons=CANCELLATION_REASONS), 400
    cancellation = CancellationRequest(registration_id=registration.id,
                                       reason=reason, details=details or None)
    db.session.add(cancellation)
    db.session.flush()
    log_activity('cancellation_requested', cancellation,
                 {'event_id': event.id, 'reason': reason})
    db.session.commit()
    notify_campus_coordinators(
        event.campus_id,
        title=f'Cancellation request: {event.title}',
        message=f'{current_user.name or current_user.email} requested cancellation for "{event.title}".',
        notification_type='cancellation_requested',
        related_event_id=event.id)
    db.session.commit()
    flash('Your cancellation request was sent for coordinator review.', 'success')
    return redirect(url_for('events.volunteer_dash'))


@events_bp.route('/volunteer_dash')
@login_required
@role_required('volunteer')
def volunteer_dash():
    profile = VolunteerProfile.query.filter_by(user_id=current_user.id).first()
    upcoming_events = Event.query.filter(
        Event.date >= datetime.now()).order_by(Event.date.asc()).all()
    recommendations = get_recommendations(
        profile, upcoming_events, campus_id=current_user.campus_id)
    total_activities = Registration.query.filter_by(
        user_id=current_user.id).count()
    cert_level = 'Active' if total_activities else 'New'
    user_stats = {'total_activities': total_activities, 'cert_level': cert_level}
    now = datetime.now()
    upcoming = Registration.query.filter_by(user_id=current_user.id).join(Event).filter(
        Event.date >= now, Registration.status.in_(('pending', 'confirmed'))
    ).order_by(Event.date.asc()).limit(5).all()
    recent_activity = Registration.query.filter_by(user_id=current_user.id).order_by(
        Registration.registered_at.desc()).limit(5).all()
    registrations = Registration.query.filter_by(user_id=current_user.id).join(Event).all()
    upcoming_registrations = [r for r in registrations if (
        r.status in ('pending', 'confirmed') and r.event.date > now)]
    history_registrations = [r for r in registrations if r not in upcoming_registrations]
    upcoming_registrations.sort(key=lambda r: r.event.date)
    history_registrations.sort(
        key=lambda r: r.registered_at or datetime.min, reverse=True)
    status_filter = request.args.get('status', '').strip()
    campus_filter = request.args.get('campus', type=int)
    category_filter = request.args.get('category', '').strip()
    start_filter = request.args.get('start_date', '').strip()
    end_filter = request.args.get('end_date', '').strip()
    filtered_registrations = registrations
    if status_filter:
        filtered_registrations = [r for r in filtered_registrations if r.status == status_filter]
    if campus_filter:
        filtered_registrations = [r for r in filtered_registrations if r.event.campus_id == campus_filter]
    if category_filter:
        filtered_registrations = [r for r in filtered_registrations if r.event.category == category_filter]
    try:
        if start_filter:
            start = datetime.fromisoformat(start_filter)
            filtered_registrations = [r for r in filtered_registrations if r.event.date >= start]
        if end_filter:
            end = datetime.fromisoformat(end_filter).replace(hour=23, minute=59, second=59)
            filtered_registrations = [r for r in filtered_registrations if r.event.date <= end]
    except ValueError:
        flash('Use valid dates for registration history filters.', 'error')
    filtered_registrations.sort(key=lambda r: r.registered_at or datetime.min, reverse=True)
    shown = max(5, request.args.get('show', 5, type=int) or 5)
    shown = min(shown, len(filtered_registrations))
    registration_items = [
        {
            'registration': r,
            'can_cancel': (
                r in upcoming_registrations
                and (r.event.cancellation_deadline or r.event.date) > now
                and not (r.cancellation_request and r.cancellation_request.status == 'pending')
            ),
            'cancellation_status': r.cancellation_request.status if r.cancellation_request else None,
        }
        for r in filtered_registrations[:shown]]
    year = request.args.get('calendar_year', now.year, type=int) or now.year
    month = request.args.get('calendar_month', now.month, type=int) or now.month
    if month < 1 or month > 12:
        year, month = now.year, now.month
    active_calendar = [r for r in upcoming_registrations if r.status == 'confirmed']
    events_by_day = {}
    for registration in active_calendar:
        if registration.event.date.year == year and registration.event.date.month == month:
            events_by_day.setdefault(registration.event.date.day, []).append(registration)
    calendar_weeks = Calendar(firstweekday=0).monthdayscalendar(year, month)
    previous_year, previous_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    campuses = Campus.query.order_by(Campus.name).all()
    categories = sorted({r.event.category for r in registrations if r.event.category})
    upcoming_schedule = [{'event': r.event, 'date': r.event.date}
                         for r in upcoming]
    certification = {'level': cert_level}
    return render_template('volunteer/Volunteer_dash.html',
                           recommendations=recommendations,
                           user_stats=user_stats,
                           recent_activity=recent_activity,
                           registration_items=registration_items,
                           registration_total=len(filtered_registrations), shown_registrations=shown,
                           registration_filters={'status': status_filter, 'campus': campus_filter,
                                                 'category': category_filter, 'start_date': start_filter,
                                                 'end_date': end_filter},
                           campuses=campuses, categories=categories,
                           calendar_year=year, calendar_month=month,
                           calendar_month_name=datetime(year, month, 1).strftime('%B %Y'),
                           calendar_weeks=calendar_weeks, calendar_events=events_by_day,
                           previous_calendar=(previous_year, previous_month),
                           next_calendar=(next_year, next_month),
                           upcoming_schedule=upcoming_schedule,
                           certification=certification)


def _dismiss_first_use_guide():
    current_user.first_use_guide_dismissed_at = datetime.utcnow()
    db.session.commit()
    if request.accept_mimetypes.best == 'application/json':
        return {'dismissed': True}
    dashboards = {
        'volunteer': 'events.volunteer_dash',
        'coordinator': 'coordinator.coordinator_dash',
        'director': 'director.director_dash',
        'admin': 'admin.admin_dash',
    }
    return redirect(url_for(dashboards.get(current_user.role, 'events.volunteer_dash')))


@events_bp.route('/guide/dismiss', methods=['POST'])
@login_required
def dismiss_first_use_guide():
    """Persist an authenticated user's decision to skip or finish the guide."""
    return _dismiss_first_use_guide()


@events_bp.route('/volunteer_dash/guide/dismiss', methods=['POST'])
@login_required
@role_required('volunteer')
def dismiss_volunteer_first_use_guide():
    """Compatibility route for the former volunteer-only guide."""
    return _dismiss_first_use_guide()


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
    agreement = _agreement_for(event)
    privacy = _privacy_for_external()
    availability_error = _external_registration_error(event)
    if request.method == 'POST':
        from_psu = request.form.get('from_psu', '').strip()
        if from_psu == 'yes':
            return redirect(url_for(
                'auth.login',
                next=url_for('events.register_for_event', event_id=event.id)))
        # Community guest path. An internal reference is generated server-side.
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        contact_number = request.form.get('contact_number', '').strip()
        if availability_error:
            flash(availability_error, 'error')
            return render_template(
                'events/event_join.html', event=event, external_form=True,
                agreement=agreement, privacy=privacy,
                availability_error=availability_error), 400
        if not name or not email:
            flash('Enter your full name and email address to register.', 'error')
            return render_template(
                'events/event_join.html', event=event, external_form=True,
                agreement=agreement, privacy=privacy), 400
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError:
            flash('Enter a valid email address.', 'error')
            return render_template(
                'events/event_join.html', event=event, external_form=True,
                agreement=agreement, privacy=privacy), 400
        if _external_registration_is_limited(email):
            flash('Too many registration attempts. Please wait and try again.', 'error')
            return render_template(
                'events/event_join.html', event=event, external_form=True,
                agreement=agreement, privacy=privacy), 429
        if (agreement is None
                or request.form.get('accept_agreement') != 'yes'
                or request.form.get('accept_privacy') != 'yes'
                or (event.nda_required
                    and request.form.get('accept_nda') != 'yes')):
            _record_external_registration_attempt(email)
            db.session.commit()
            flash('Accept the required agreement(s) before joining.', 'error')
            return render_template('events/event_join.html', event=event, external_form=True,
                                   agreement=agreement, privacy=privacy), 400
        participant = _guest_external_participant(name, email, contact_number)
        existing = Registration.query.filter_by(
            external_participant_id=participant.id, event_id=event.id).first()
        if existing is None:
            registration = Registration(
                external_participant_id=participant.id, event_id=event.id,
                status='confirmed', policy_accepted_at=datetime.utcnow(),
                policy_version=agreement['version'],
                nda_accepted_at=datetime.utcnow() if event.nda_required else None,
                nda_version=event.nda_version if event.nda_required else None,
                external_privacy_accepted_at=datetime.utcnow(),
                external_privacy_version=privacy['version'])
            db.session.add(registration)
            db.session.flush()
            log_activity('external_registration', registration,
                         {'event_id': event.id, 'privacy_version': privacy['version']})
            _record_external_registration_attempt(email)
            db.session.commit()
            notify_campus_coordinators(
                event.campus_id,
                title=f'New external volunteer: {event.title}',
                message=f'An external volunteer ({participant.name or participant.id_number}) '
                        f'registered for "{event.title}".',
                notification_type='external_registration',
                related_event_id=event.id)
            db.session.commit()
            _send_external_confirmation(registration)
            flash('Registration received. Check your email for the confirmation and management link.',
                  'success')
        else:
            _record_external_registration_attempt(email)
            db.session.commit()
            _send_external_confirmation(existing)
            flash('A registration for this activity already exists. Check your email for its details.',
                  'info')
        return redirect(url_for('events.opportunities'))

    external_form = request.args.get('external') == '1'
    return render_template('events/event_join.html', event=event, external_form=external_form,
                           agreement=agreement, privacy=privacy,
                           availability_error=availability_error)


@events_bp.route('/external/registrations/<token>')
def external_registration_manage(token):
    """Show a guest only the registration represented by their signed link."""
    try:
        registration = _external_registration_from_token(token)
    except (BadSignature, SignatureExpired):
        return render_template('events/external_registration_unavailable.html'), 404
    return render_template(
        'events/external_registration_manage.html',
        registration=registration,
        token=token,
        can_cancel=_external_cancellation_available(registration),
        reasons=CANCELLATION_REASONS,
    )


@events_bp.route('/external/registrations/<token>/cancel', methods=['POST'])
def external_registration_cancel(token):
    """Accept a signed guest cancellation request for coordinator review."""
    try:
        registration = _external_registration_from_token(token)
    except (BadSignature, SignatureExpired):
        return render_template('events/external_registration_unavailable.html'), 404
    if not _external_cancellation_available(registration):
        flash('Cancellation is unavailable because the deadline passed or a request is already pending.',
              'error')
        return redirect(url_for('events.external_registration_manage', token=token))
    reason = request.form.get('reason', '').strip()
    details = request.form.get('details', '').strip()
    if reason not in CANCELLATION_REASONS or (reason == 'Other' and not details):
        flash('Choose a cancellation reason. Explain Other reasons.', 'error')
        return redirect(url_for('events.external_registration_manage', token=token))
    cancellation = CancellationRequest(
        registration_id=registration.id,
        reason=reason,
        details=details or None,
    )
    db.session.add(cancellation)
    db.session.flush()
    log_activity('cancellation_requested', cancellation,
                 {'event_id': registration.event_id, 'reason': reason,
                  'external': True})
    db.session.commit()
    notify_campus_coordinators(
        registration.event.campus_id,
        title=f'Cancellation request: {registration.event.title}',
        message=(f'{registration.external_participant.name or "External volunteer"} '
                 f'requested cancellation for "{registration.event.title}".'),
        notification_type='cancellation_requested',
        related_event_id=registration.event_id,
    )
    db.session.commit()
    flash('Your cancellation request was sent for coordinator review.', 'success')
    return redirect(url_for('events.external_registration_manage', token=token))
