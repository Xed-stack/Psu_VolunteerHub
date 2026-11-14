"""Connected, role-scoped activity and reporting screens."""
import csv
import io
import json
import uuid
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import MultiDict
from app.models import db
from app.models.user import User, Skill
from app.models.event import Event, Registration, Attendance, Campus, ExternalParticipant, SdgGoal
from app.models.workspace import FormDraft, PartnerAgency, PartnerAgreement, ExternalGroup
from app.models.notification import notify
from app.services.activity_workflow import attendance_open, local_now, save_document
from app.utils.decorators import roles_required, role_required
from app.utils.audit import log_activity

workspace_bp = Blueprint('workspace', __name__, url_prefix='/workspace')
ACTIVITY_FIELDS = {'title', 'description', 'date', 'end_date', 'location', 'category', 'slots',
                   'cancellation_days', 'required_skills', 'sdg_ids', 'target_participants',
                   'conducting_department', 'participant_type', 'departments', 'agreement_id'}
REMOVED_ACTIVITY_FIELDS = {'participation_agreement_text', 'participation_agreement_version',
                           'nda_required', 'nda_text', 'nda_version', 'volunteer_ids'}
# Only these form fields can ever be persisted by browser autosave.
FORM_FIELDS = ACTIVITY_FIELDS | {'name', 'full_name', 'email', 'phone', 'contact_name',
    'campus', 'campus_id', 'college_affiliation', 'volunteer_type', 'sex', 'id_number',
    'interest_ids', 'skill_ids', 'reference', 'valid_from', 'valid_until', 'notes',
    'program', 'indicator', 'definition', 'unit', 'target_value', 'deadline', 'evidence_basis',
    'source_document', 'coverage_note', 'actual_value', 'year', 'plan_type', 'title', 'description', 'first_name', 'last_name', 'skills', 'interests', 'responsible_office', 'comparison_rule', 'coverage_start', 'coverage_end', 'note', 'code', 'unit', 'program', 'college_affiliation_add', 'college_affiliation_remove', 'default_password_length', 'max_slots_per_event', 'nda_text', 'nda_version', 'nda_required', 'participation_agreement_version', 'message', 'announcement_type'}


@workspace_bp.before_app_request
def restore_draft_uploads():
    if request.method != 'POST' or not current_user.is_authenticated:
        return
    key = request.form.get('_draft_key', '')
    if not key.startswith('form:'):
        return
    draft = draft_for(key)
    if not draft:
        return
    from werkzeug.datastructures import FileStorage
    files = MultiDict(request.files)
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'draft-uploads'
    for name, meta in draft.payload.get('_files', {}).items():
        if files.get(name) and files[name].filename:
            continue
        path = folder / Path(meta['path']).name
        if path.is_file():
            files[name] = FileStorage(io.BytesIO(path.read_bytes()), filename=meta['name'])
    request.files = files


@workspace_bp.after_app_request
def clear_submitted_draft(response):
    if request.method == 'POST' and current_user.is_authenticated and response.status_code in (302, 303):
        key = request.form.get('_draft_key', '')
        from flask import session
        failed = any(category in ('error', 'warning', 'danger') for category, _ in session.get('_flashes', []))
        if key.startswith('form:') and not failed:
            draft = draft_for(key)
            if draft:
                files = draft.payload.get('_files', {})
                db.session.delete(draft)
                db.session.commit()
                remove_staged_files(files)
    return response


@workspace_bp.route('/draft-uploads/<path:key>', methods=['POST'])
@login_required
def draft_upload(key):
    if len(key) > 160 or (not key.startswith('form:/') and key != 'activity:new') or key.startswith('form://') or '\\' in key:
        abort(400)
    if key == 'activity:new' and current_user.role != 'coordinator':
        abort(403)
    name = request.form.get('field')
    file = request.files.get('upload')
    if name not in ('document', 'file', 'profile_image', 'cover_image', 'evidence_file') or not file or not file.filename:
        abort(400)
    from werkzeug.utils import secure_filename
    import uuid
    filename = secure_filename(file.filename)
    if Path(filename).suffix.lower() not in ('.pdf', '.docx', '.png', '.jpg', '.jpeg', '.webp'):
        abort(400)
    content = file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        abort(413)
    if name == 'cover_image':
        from app.services.activity_workflow import validate_cover
        try:
            validate_cover(content,filename)
        except ValueError as exc:
            abort(400,description=str(exc))
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'draft-uploads'
    folder.mkdir(parents=True, exist_ok=True)
    path = uuid.uuid4().hex
    (folder / path).write_bytes(content)
    draft = draft_for(key, create=True)
    saved = dict(draft.payload.get('_files', {}))
    previous = saved.get(name)
    saved[name] = {'path': path, 'name': filename}
    draft.payload = dict(draft.payload, _files=saved)
    db.session.commit()
    if previous:
        remove_staged_files({name: previous})
    return jsonify(name=filename)


def remove_staged_files(files):
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'draft-uploads'
    for document in files.values():
        try:
            (folder / Path(document['path']).name).unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning('A discarded draft attachment could not be removed.')


def scoped_events():
    query = Event.query
    if current_user.role == 'coordinator':
        if not current_user.campus_id:
            abort(403)
        query = query.filter_by(campus_id=current_user.campus_id)
    elif current_user.role not in ('director', 'admin'):
        abort(403)
    return query


def owned_event(event_id, lock=False):
    query = scoped_events().filter_by(id=event_id)
    if lock:
        query = query.populate_existing().with_for_update()
    return query.first_or_404()


def draft_for(key, create=False):
    query = FormDraft.query.filter_by(user_id=current_user.id, key=key)
    if request.method in ('PUT', 'POST', 'DELETE'):
        query = query.populate_existing().with_for_update()
    draft = query.first()
    if draft and draft.campus_id != current_user.campus_id:
        abort(403)
    if draft is None and create:
        draft = FormDraft(user_id=current_user.id, campus_id=current_user.campus_id, key=key, payload={})
        db.session.add(draft)
    return draft


def activity_draft_key(key):
    path = key.split('?', 1)[0]
    prefix = 'form:/coordinator/events/'
    return key == 'activity:new' or (path.startswith(prefix) and path.endswith('/edit')
                                   and path[len(prefix):-len('/edit')].isdigit())


def clean_activity_draft(draft):
    if draft and activity_draft_key(draft.key) and REMOVED_ACTIVITY_FIELDS.intersection(draft.payload):
        draft.payload = {key: value for key, value in draft.payload.items() if key not in REMOVED_ACTIVITY_FIELDS}
        return True
    return False


@workspace_bp.route('/drafts/<path:key>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def drafts(key):
    if len(key) > 160 or not key.startswith(('form:', 'activity:')):
        abort(400)
    if key.startswith('form:') and (not key[5:].startswith('/') or key[5:].startswith('//') or '\\' in key or any(ord(c) < 32 for c in key)):
        abort(400)
    if key.startswith('activity:') and current_user.role != 'coordinator':
        abort(403)
    draft = draft_for(key, create=request.method == 'PUT')
    if clean_activity_draft(draft):
        db.session.commit()
    if request.method == 'DELETE':
        if draft:
            files = draft.payload.get('_files', {})
            db.session.delete(draft)
            db.session.commit()
            remove_staged_files(files)
        return '', 204
    if request.method == 'PUT':
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or len(json.dumps(data)) > 60000:
            abort(400)
        clean = {}
        for name, value in data.items():
            if name not in (ACTIVITY_FIELDS if key == 'activity:new' else FORM_FIELDS):
                continue
            if activity_draft_key(key) and name in REMOVED_ACTIVITY_FIELDS:
                continue
            values = value if isinstance(value, list) else [value]
            if len(values) > 200 or any(not isinstance(v, str) or len(v) > 10000 for v in values):
                abort(400)
            clean[name] = values
        # Upload metadata is written only by the authenticated upload route.
        draft.payload = dict(draft.payload, **clean)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify(error='Another tab saved this draft. Reload before continuing.'), 409
    return jsonify(payload=draft.payload if draft else {}, updated_at=draft.updated_at.isoformat() if draft else None)


@workspace_bp.route('/drafts')
@login_required
def draft_list():
    rows = FormDraft.query.filter_by(user_id=current_user.id, campus_id=current_user.campus_id).order_by(FormDraft.updated_at.desc()).all()
    from urllib.parse import urlsplit
    from werkzeug.exceptions import HTTPException
    labels = {'volunteer.profile_page':'Profile preferences', 'volunteer.change_name':'Name changes',
        'admin.settings':'System settings', 'workspace.partners':'New partner agency',
        'workspace.partner':'New MOA', 'workspace.activity_documents':'Activity documents and announcement', 'coordinator.edit_activity':'Activity changes',
        'admin.create_user':'New account', 'admin.edit_user':'Account changes',
        'goals.edit':'Annual goal proposal', 'goals.evidence':'Annual goal evidence'}
    for draft in rows:
        draft.label = 'New activity' if draft.key == 'activity:new' else 'Unfinished form'
        if draft.key.startswith('form:'):
            try:
                endpoint, _ = current_app.url_map.bind('').match(urlsplit(draft.key[5:]).path, method='GET')
                draft.label = labels.get(endpoint, 'Unfinished form')
            except HTTPException:
                pass
    return render_template('workspace/drafts.html', drafts=rows)


@workspace_bp.route('/activities')
@login_required
@roles_required('coordinator', 'director', 'admin')
def activities():
    query = scoped_events()
    state = request.args.get('state', 'upcoming')
    now = local_now()
    if state == 'upcoming':
        query = query.filter(Event.date > now, Event.lifecycle_status == 'approved')
    elif state == 'ongoing':
        query = query.filter(Event.date <= now, Event.end_date > now, Event.lifecycle_status == 'approved')
    elif state == 'past':
        query = query.filter(func.coalesce(Event.end_date, Event.date) <= now)
    elif state == 'cancelled':
        query = query.filter(Event.lifecycle_status == 'cancelled')
    elif state != 'all':
        abort(400)
    search = request.args.get('q', '').strip()[:200]
    if search:
        query = query.filter(or_(Event.title.icontains(search, autoescape=True),
                                 Event.description.icontains(search, autoescape=True)))
    category = request.args.get('category', '').strip()
    if category:
        query = query.filter_by(category=category)
    campus = request.args.get('campus_id', type=int)
    if campus and current_user.role != 'coordinator':
        query = query.filter_by(campus_id=campus)
    pagination = db.paginate(query.order_by(Event.date.asc() if state in ('upcoming', 'ongoing') else Event.date.desc(), Event.id).statement,
                             per_page=15, max_per_page=15, error_out=False)
    categories = [row[0] for row in scoped_events().with_entities(Event.category).filter(Event.category.isnot(None)).distinct().order_by(Event.category)]
    return render_template('workspace/activities.html', pagination=pagination, state=state, search=search, now=now,
                           categories=categories, campuses=Campus.query.order_by(Campus.name).all())


@workspace_bp.route('/activities/<int:event_id>')
@login_required
@roles_required('coordinator', 'director', 'admin')
def activity(event_id):
    event = owned_event(event_id)
    counts = dict(db.session.query(Registration.status, func.count(Registration.id)).filter_by(event_id=event.id).group_by(Registration.status).all())
    unrecorded = Registration.query.filter(Registration.event_id == event.id,
        Registration.status != 'cancelled', ~Registration.attendance_record.has()).count()
    actual_present = db.session.query(func.count(Attendance.id)).join(Registration,Registration.id == Attendance.registration_id).filter(
        Registration.event_id == event.id,Registration.status != 'cancelled',Attendance.status == 'present').scalar()
    return render_template('workspace/activity.html', event=event, counts=counts, unrecorded=unrecorded,
                           now=local_now(), editable=attendance_open(event),actual_present=actual_present)


@workspace_bp.route('/activities/<int:event_id>/cancel', methods=['POST'])
@login_required
@role_required('coordinator')
def cancel_activity(event_id):
    event = owned_event(event_id, lock=True)
    reason = request.form.get('reason', '').strip()
    if not 3 <= len(reason) <= 2000 or event.lifecycle_status != 'approved' or (event.end_date and event.end_date <= local_now()):
        abort(400, description='Provide a reason for cancelling an upcoming or ongoing approved activity.')
    event.lifecycle_status = 'cancelled'
    event.cancellation_reason = reason
    event.cancelled_at = datetime.utcnow()
    registrations = Registration.query.filter(Registration.event_id == event.id, Registration.status.in_(('pending', 'confirmed'))).all()
    for registration in registrations:
        registration.status = 'cancelled'
        if registration.user_id:
            notify(registration.user_id, 'Activity cancelled', f'{event.title}: {reason}', 'activity_cancelled', event.id, commit=False)
    log_activity('activity_cancelled', event, {'reason': reason})
    db.session.commit()
    flash('Activity cancelled. Its records have been preserved.', 'success')
    return redirect(url_for('workspace.activity', event_id=event.id))


@workspace_bp.route('/create/<int:step>', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def create_activity(step):
    if step not in (1, 2, 3, 4) or not current_user.campus_id:
        abort(404 if step not in (1, 2, 3, 4) else 403)
    draft = draft_for('activity:new', create=True)
    if clean_activity_draft(draft):
        db.session.commit()
    from copy import deepcopy
    data = deepcopy(draft.payload or {})
    errors = []
    if step > 1 and not data.get('_proposal'):
        return redirect(url_for('workspace.create_activity', step=1))
    if request.method == 'POST':
        if step == 1:
            try:
                file = request.files.get('proposal')
                if file and file.filename or not data.get('_proposal'):
                    document, extracted = save_document(file)
                    data = dict(data, _proposal=document)
                    for key, value in extracted.items():
                        if not data.get(key):
                            data[key] = [value]
                    flash('Proposal saved. Review extracted details before publishing.' if document['readable'] else
                          'Proposal saved. Its text could not be extracted; enter the activity details manually.', 'info')
            except ValueError as exc:
                errors.append(str(exc))
        else:
            for key in ACTIVITY_FIELDS:
                if key in request.form:
                    data[key] = request.form.getlist(key)
            if step == 2:
                data['required_skills'] = request.form.getlist('required_skills')
                data['sdg_ids'] = request.form.getlist('sdg_ids')
                file = request.files.get('cover_image')
                if file and file.filename:
                    from app.services.activity_workflow import stage_cover
                    try:
                        metadata = stage_cover(file)
                        saved = dict(data.get('_files',{}))
                        previous = saved.get('cover_image')
                        saved['cover_image'] = metadata
                        data['_files'] = saved
                        if previous:
                            remove_staged_files({'cover_image':previous})
                    except ValueError as exc:
                        errors.append(str(exc))
            if step == 3:
                data['departments'] = request.form.getlist('departments')
        draft.payload = dict(data)
        if not errors and step == 4:
            event, errors = publish_draft(data)
            if not errors:
                db.session.add(event)
                db.session.flush()
                notify_audience(event)
                log_activity('activity_created', event, {'proposal': True})
                staged = data.get('_files',{})
                db.session.delete(draft)
                db.session.commit()
                remove_staged_files(staged)
                flash('Approved activity published.', 'success')
                return redirect(url_for('workspace.activity', event_id=event.id))
        db.session.commit()
        if not errors:
            return redirect(url_for('workspace.create_activity', step=step + 1))
    data = MultiDict((key, value) for key, values in data.items() if not key.startswith('_')
                     for value in (values if isinstance(values, list) else [values]))
    from app.routes.coordinator import _activity_categories, _max_event_slots
    return render_template('workspace/create.html', step=step, data=data, errors=errors,
        proposal=draft.payload.get('_proposal'), saved_cover=draft.payload.get('_files',{}).get('cover_image'), skills=Skill.query.order_by(Skill.name).all(),
        sdgs=SdgGoal.query.order_by(SdgGoal.number).all(), categories=_activity_categories(),
        max_slots=_max_event_slots(), now=local_now(),
        agencies=PartnerAgency.query.filter_by(campus_id=current_user.campus_id).all(),
        departments=audience_departments())


def publish_draft(payload):
    form = MultiDict((key, value) for key, values in payload.items() if key in ACTIVITY_FIELDS
                     for value in (values if isinstance(values, list) else [values]))
    from app.routes.coordinator import _activity_categories, _max_event_slots, _parse_event_schedule
    errors = []
    schedule, error = _parse_event_schedule(form)
    if error:
        errors.append(error)
    elif not schedule[1] or schedule[0] <= local_now() or schedule[0].tzinfo or schedule[1].tzinfo:
        errors.append('Choose a future start and a later end time in Philippine local time.')
    if not form.get('title', '').strip() or not form.get('description', '').strip():
        errors.append('Title and description are required.')
    if len(form.get('title', '')) > 200:
        errors.append('The title must be 200 characters or fewer.')
    if form.get('category') not in _activity_categories():
        errors.append('Choose an available category.')
    slots = form.get('slots', type=int)
    if slots is None or not 1 <= slots <= _max_event_slots():
        errors.append('Choose a valid number of volunteer slots.')
    target = form.get('target_participants', type=int)
    if form.get('target_participants') and (target is None or target < 1):
        errors.append('The numeric participant target must be positive.')
    skills = Skill.query.filter(Skill.id.in_(form.getlist('required_skills'))).all()
    sdgs = SdgGoal.query.filter(SdgGoal.id.in_(form.getlist('sdg_ids'))).all()
    if len(skills) != len(set(form.getlist('required_skills'))) or len(sdgs) != len(set(form.getlist('sdg_ids'))):
        errors.append('Choose available skills and goals.')
    if SdgGoal.query.count() and not sdgs:
        errors.append('Select at least one Sustainable Development Goal.')
    agreement = None
    if form.get('agreement_id'):
        agreement = PartnerAgreement.query.join(PartnerAgency).filter(
            PartnerAgreement.id == form.get('agreement_id', type=int), PartnerAgency.campus_id == current_user.campus_id).first()
        if not agreement or (schedule and not agreement.valid_from <= schedule[0].date() <= agreement.valid_until):
            errors.append('Choose a campus MOA valid on the activity date.')
    if not set(form.getlist('departments')) <= set(audience_departments()):
        errors.append('Choose audience departments from the campus list.')
    if not payload.get('_proposal'):
        errors.append('Upload the approved proposal first.')
    if errors:
        return None, errors
    event = Event(title=form['title'].strip(), description=form['description'].strip(), date=schedule[0],
        end_date=schedule[1], cancellation_deadline=schedule[2], location=form.get('location', ''),
        category=form['category'], slots=slots, target_participants=target,
        campus_id=current_user.campus_id, created_by_id=current_user.id, proposal_document=payload['_proposal'],
        conducting_department=form.get('conducting_department', '')[:150], participant_type=form.get('participant_type', '')[:100],
        audience={'departments': form.getlist('departments')},
        agreement_id=agreement.id if agreement else None)
    cover = payload.get('_files',{}).get('cover_image')
    if cover:
        from werkzeug.datastructures import FileStorage
        from app.routes.coordinator import _save_event_cover
        path = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'draft-uploads' / Path(cover['path']).name
        if not path.is_file():
            return None, ['The saved cover is unavailable. Return to Activity Details to upload it again.']
        try:
            saved = _save_event_cover(FileStorage(io.BytesIO(path.read_bytes()),filename=cover['name']))
        except ValueError as exc:
            return None, [str(exc)]
        event.cover_image_path = saved['path']
        event.cover_image_name = saved['original_name']
        event.cover_uploaded_by_id = current_user.id
        event.cover_uploaded_at = datetime.utcnow()
    event.required_skills_rel = skills
    event.sdgs = sdgs
    return event, []


def audience_departments():
    from app.campuses import campus_affiliations
    stored = [row[0] for row in db.session.query(User.college_affiliation).filter(
        User.campus_id == current_user.campus_id, User.college_affiliation.isnot(None)).distinct().all()]
    return sorted(set(campus_affiliations(current_user.campus) + stored))


def notify_audience(event):
    audience = event.audience or {}
    volunteers = User.query.filter_by(role='volunteer', campus_id=event.campus_id, _is_active=True)
    recipients = volunteers.filter(or_(User.id.in_(audience.get('volunteer_ids', [])),
        User.college_affiliation.in_(audience.get('departments', [])))).all()
    for user in recipients:
        notify(user.id, 'An activity for your campus', event.title, 'activity_invitation', event.id, commit=False)


@workspace_bp.route('/activities/<int:event_id>/proposal')
@login_required
@roles_required('coordinator', 'director', 'admin')
def proposal(event_id):
    event = owned_event(event_id)
    document = event.proposal_document
    if not document:
        abort(404)
    return private_document(document)


def private_document(document):
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'proposals'
    path = folder / Path(document['path']).name
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=document['name'])


@workspace_bp.route('/partners', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def partners():
    if not current_user.campus_id:
        abort(403)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact = request.form.get('contact_name', '').strip()
        if not name or not contact or len(name) > 200 or len(contact) > 150:
            abort(400, description='Agency name and contact person are required.')
        agency = PartnerAgency(name=name, contact_name=contact, campus_id=current_user.campus_id,
            email=request.form.get('email', '').strip()[:120], phone=request.form.get('phone', '').strip()[:50])
        db.session.add(agency)
        db.session.commit()
        return redirect(url_for('workspace.partner', agency_id=agency.id))
    query = PartnerAgency.query.filter_by(campus_id=current_user.campus_id)
    search = request.args.get('q', '').strip()[:200]
    if search:
        query = query.filter(or_(PartnerAgency.name.icontains(search, autoescape=True),
                                 PartnerAgency.contact_name.icontains(search, autoescape=True)))
    pagination = db.paginate(query.order_by(PartnerAgency.name, PartnerAgency.id).statement,
                             per_page=25, max_per_page=25, error_out=False)
    return render_template('workspace/partners.html', agencies=pagination.items, pagination=pagination)


@workspace_bp.route('/partners/<int:agency_id>', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def partner(agency_id):
    agency = PartnerAgency.query.filter_by(id=agency_id, campus_id=current_user.campus_id).first_or_404()
    errors = []
    if request.method == 'POST':
        try:
            start = date.fromisoformat(request.form.get('valid_from', ''))
            end = date.fromisoformat(request.form.get('valid_until', ''))
            reference = request.form.get('reference', '').strip()
            if end < start or not reference or len(reference) > 150:
                raise ValueError('Provide a reference and valid agreement dates.')
            document, _ = save_document(request.files.get('document'))
            db.session.add(PartnerAgreement(agency_id=agency.id, reference=reference, valid_from=start, valid_until=end, document=document))
            db.session.commit()
            return redirect(url_for('workspace.partner', agency_id=agency.id))
        except ValueError as exc:
            errors.append(str(exc))
    return render_template('workspace/partner.html', agency=agency, errors=errors)


@workspace_bp.route('/partners/<int:agency_id>/moa/<int:agreement_id>')
@login_required
@role_required('coordinator')
def moa(agency_id, agreement_id):
    agency = PartnerAgency.query.filter_by(id=agency_id, campus_id=current_user.campus_id).first_or_404()
    agreement = PartnerAgreement.query.filter_by(id=agreement_id, agency_id=agency.id).first_or_404()
    return private_document(agreement.document)


@workspace_bp.route('/activities/<int:event_id>/external', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def external(event_id):
    event = owned_event(event_id, lock=request.method == 'POST')
    errors = []
    if request.method == 'POST':
        if not attendance_open(event):
            abort(409, description='External attendance can only be recorded while the activity is ongoing.')
        if request.form.get('action') == 'attendance':
            ids = request.form.getlist('registration_id', type=int)
            statuses = request.form.getlist('status')
            if len(ids) > 100 or len(ids) != len(set(ids)) or len(statuses) != len(ids):
                abort(400)
            rows = Registration.query.filter(Registration.id.in_(ids), Registration.event_id == event.id,
                Registration.external_participant_id.isnot(None), Registration.status != 'cancelled').with_for_update().all()
            if len(rows) != len(ids):
                abort(403)
            values = dict(zip(ids, statuses))
            for row in rows:
                status = values[row.id]
                if not status:
                    continue
                if status not in ('present', 'absent', 'excused'):
                    abort(400)
                if row.attendance_record:
                    row.attendance_record.status = status
                else:
                    db.session.add(Attendance(registration_id=row.id, event_id=event.id, status=status))
            if not attendance_open(event):
                db.session.rollback()
                abort(409)
            db.session.commit()
            flash('External attendance saved.', 'success')
            return redirect(url_for('workspace.external', event_id=event.id))
        group_name = request.form.get('group_name', '').strip()[:150]
        raw = request.form.get('roster', '')
        upload = request.files.get('roster_file')
        if upload and upload.filename:
            try:
                raw = upload.read(100001).decode('utf-8-sig')
            except UnicodeError:
                abort(400, description='Use a UTF-8 CSV file.')
        rows = list(csv.reader(io.StringIO(raw))) if len(raw) <= 100000 else []
        if not rows or len(rows) > 100 or any(not r or not r[0].strip() or len(r[0]) > 100 for r in rows):
            errors.append('Enter 1–100 named people, one per line: name,email (email optional).')
        else:
            group = ExternalGroup(event_id=event.id, name=group_name or 'Individual volunteers')
            db.session.add(group)
            db.session.flush()
            import uuid
            for row in rows:
                person = ExternalParticipant(id_number='EXT-' + uuid.uuid4().hex, name=row[0].strip(),
                    email=row[1].strip()[:120] if len(row) > 1 else None, group_id=group.id)
                db.session.add(person)
                db.session.flush()
                registration = Registration(event_id=event.id, external_participant_id=person.id, status='confirmed')
                db.session.add(registration)
                db.session.flush()
                if request.form.get('mark_present') == 'yes':
                    db.session.add(Attendance(registration_id=registration.id, event_id=event.id, status='present'))
            if not attendance_open(event):
                db.session.rollback()
                abort(409, description='The activity ended before the roster was saved.')
            db.session.commit()
            flash('Named external roster saved.', 'success')
            return redirect(url_for('workspace.external', event_id=event.id))
    groups = ExternalGroup.query.filter_by(event_id=event.id).all()
    query = Registration.query.join(ExternalParticipant).filter(Registration.event_id == event.id,
        Registration.external_participant_id.isnot(None), Registration.status != 'cancelled')
    search = request.args.get('q', '').strip()[:200]
    if search:
        query = query.filter(or_(ExternalParticipant.name.icontains(search, autoescape=True),
                                 ExternalParticipant.email.icontains(search, autoescape=True)))
    attendance_status = request.args.get('attendance_status', '')
    if attendance_status == 'unmarked':
        query = query.filter(~Registration.attendance_record.has())
    elif attendance_status in ('present', 'absent', 'excused'):
        query = query.filter(Registration.attendance_record.has(Attendance.status == attendance_status))
    elif attendance_status:
        abort(400)
    pagination = db.paginate(query.order_by(ExternalParticipant.name, Registration.id).statement,
                             per_page=25, max_per_page=25, error_out=False)
    return render_template('workspace/external.html', event=event, groups=groups, registrations=pagination.items,
                           pagination=pagination, errors=errors, editable=attendance_open(event))


def report_data(args=None, forced_campus=None):
    from app.services.workspace_reports import workspace_report
    return workspace_report(scoped_events(), args if args is not None else request.args,
                            current_user, local_now(), forced_campus)


@workspace_bp.route('/overview')
@login_required
@roles_required('director', 'admin', 'coordinator')
def overview():
    from app.services.workspace_reports import follow_up_items
    from app.services.staff_overview import overview_context
    data = report_data()
    findings = follow_up_items(data)
    agenda = []
    if current_user.role == 'coordinator':
        now = data['now']
        agenda = scoped_events().filter(Event.lifecycle_status == 'approved',
            or_(Event.date > now, db.and_(Event.date <= now, Event.end_date > now))
        ).order_by(Event.date, Event.id).limit(5).all()
    return render_template('workspace/overview.html', **data, **overview_context(data, findings),
                           follow_ups=findings, agenda=agenda)


@workspace_bp.route('/reports')
@login_required
@roles_required('director', 'admin', 'coordinator')
def reports():
    return render_template('workspace/reports.html')


@workspace_bp.route('/follow-up')
@login_required
@roles_required('director', 'admin', 'coordinator')
def follow_up():
    from app.services.workspace_reports import follow_up_items
    data = report_data()
    items = follow_up_items(data)
    # The queue is bounded in the UI even when the report scope spans many years.
    page = request.args.get('page',1,type=int)
    if page is None or page < 1:
        abort(400)
    return render_template('workspace/follow_up.html', **data, items=items[(page-1)*25:page*25],
                           total=len(items), page=page, pages=max(1,(len(items)+24)//25))


@workspace_bp.route('/campuses/<int:campus_id>')
@login_required
@roles_required('director', 'admin')
def campus(campus_id):
    campus = db.session.get(Campus,campus_id)
    if not campus:
        abort(404)
    from app.services.workspace_reports import follow_up_items
    data = report_data(forced_campus=campus.id)
    return render_template('workspace/campus.html', **data, campus=campus, follow_ups=follow_up_items(data))


@workspace_bp.route('/recognition')
@login_required
@roles_required('director', 'admin')
def recognition():
    year = request.args.get('award_year',local_now().year,type=int)
    if year is None or not 1900 <= year <= 9998:
        abort(400,description='Choose a valid recognition year.')
    from app.recommendation.analytics import AnalyticsAggregator
    return render_template('workspace/recognition.html',award_year=year,
                           leaderboards=AnalyticsAggregator.award_leaderboards(year))


@workspace_bp.route('/reports/people')
@login_required
@roles_required('director', 'admin', 'coordinator')
def people_insights():
    from app.models.user import Interest, user_skills, user_interests
    campus_id = current_user.campus_id if current_user.role == 'coordinator' else request.args.get('campus_id',type=int)
    users = User.query
    if current_user.role == 'coordinator' and not campus_id:
        abort(403)
    if campus_id:
        users = users.filter_by(campus_id=campus_id)
    ids = users.with_entities(User.id).statement
    roles = users.with_entities(User.role,func.count(User.id)).group_by(User.role).order_by(User.role).all()
    def popular(model, junction, column):
        return db.session.query(model.name,func.count(junction.c.user_id)).join(
            junction, model.id == column).filter(junction.c.user_id.in_(ids)).group_by(model.id,model.name).order_by(
            func.count(junction.c.user_id).desc(),model.name).limit(10).all()
    return render_template('workspace/people_insights.html',total=users.count(),roles=roles,
        skills=popular(Skill,user_skills,user_skills.c.skill_id),
        interests=popular(Interest,user_interests,user_interests.c.interest_id),
        campus_id=campus_id,campuses=Campus.query.order_by(Campus.name).all())


@workspace_bp.route('/reports/results')
@login_required
@roles_required('director', 'admin', 'coordinator')
def report_results():
    data = report_data()
    view = request.args.get('view', 'summary')
    if view not in ('summary', 'activities', 'participation'):
        view = 'summary'
    page = request.args.get('page', 1, type=int)
    total = len(data['rows'])
    pages = max(1, (total + 24) // 25)
    if not 1 <= page <= pages:
        abort(404)
    data['rows'] = data['rows'][(page - 1) * 25:page * 25]
    return render_template('workspace/results.html', **data, page=page, pages=pages, total=total, report_view=view)


@workspace_bp.route('/reports/activities/<int:event_id>')
@login_required
@roles_required('director', 'admin', 'coordinator')
def activity_report(event_id):
    """Read one authorized activity using the same effective scope as its exports."""
    event = owned_event(event_id)
    args = request.args.copy()
    args.setlist('event_id', [str(event.id)])
    args.setdefault('period', 'all')
    args.setdefault('year', str(event.date.year))
    data = report_data(args)
    row = next((row for row in data['rows'] if row['event'].id == event.id), None)
    if row is None:
        abort(404, description='This activity is outside the selected report scope.')
    roster = None
    if event.date <= local_now():
        query = Registration.query.filter_by(event_id=event.id).options(
            joinedload(Registration.user), joinedload(Registration.external_participant),
            joinedload(Registration.attendance_record)).order_by(Registration.id)
        roster = db.paginate(query.statement, page=max(1, request.args.get('roster_page', 1, type=int)),
                             per_page=25, error_out=False)
    return render_template('workspace/activity_report.html', **data, row=row, event=event,
                           roster=roster, export_query=args.to_dict(flat=False))


@workspace_bp.route('/reports/aop')
@login_required
@roles_required('director', 'admin', 'coordinator')
def aop():
    data = report_data()
    from app.annual_goals import summarize
    data['campus_rollup'] = summarize([row for campus in data['campus_goals'] for row in campus['rows']], data['year'])
    groups = {}
    for row in data['goals']['rows']:
        if 'AOP' in row['plan_types'] and row['verified']:
            groups.setdefault(row['unit'], []).append(dict(name=row['name'], target=float(row['target']), actual=float(row['actual'])))
    data['target_groups'] = groups
    return render_template('workspace/aop.html', **data)


@workspace_bp.route('/reports/export/<format>')
@login_required
@roles_required('director', 'admin', 'coordinator')
def export(format):
    if format not in ('csv', 'pdf', 'xlsx'):
        abort(404)
    data = report_data()
    if request.args.get('sample') == '1':
        abort(400, description='Sample data cannot be exported as an official report.')
    if request.args.get('report') == 'aop':
        return export_aop(data, format)
    from app.reports import csv_safe
    headers = ['Activity', 'Campus', 'Conducting department', 'Start (Philippine time)', 'Status', 'Conducted', 'Recorded attendees']
    values = [[r['event'].title, r['event'].campus.name if r['event'].campus else 'Unassigned',
               r['event'].conducting_department or 'Not recorded', str(r['event'].date), r['event'].lifecycle_status,
               'Yes' if r['conducted'] else 'No', r['attendees']] for r in data['rows']]
    supplemental_headers = ['Registrations','Internal','External','Recorded present','Completed participation','Attendance rate (%)','Numeric participant target','Target outcome','Attendance recording']
    supplemental_values = [[r['metrics']['registrations'],r['metrics']['internal'],r['metrics']['external'],
        r['metrics']['present'],r['metrics']['completed'],r['metrics']['rate'] if r['metrics']['rate'] is not None else 'Pending / unavailable',
        r['event'].target_participants if r['event'].target_participants is not None else 'Not set',
        'Met' if r['metrics']['target_met'] is True else 'Not reached' if r['metrics']['target_met'] is False else 'Pending / unavailable',
        'Complete' if r['metrics']['complete'] else 'End time not recorded' if not r['event'].end_date else 'Incomplete' if r['conducted'] else 'Upcoming / ongoing'] for r in data['rows']]
    headers += supplemental_headers
    for row,extra in zip(values,supplemental_values):
        row.extend(extra)
    roster_headers = ['Volunteer', 'Participant type', 'Registration', 'Attendance']
    roster = []
    if data['event_id'] and data['rows'] and data['rows'][0]['event'].date <= local_now():
        for reg in data['rows'][0]['event'].registrations:
            roster.append([reg.participant.name if reg.participant else 'Not recorded',
                'External' if reg.is_external else 'Account', reg.status,
                {'present':'Attending', 'absent':'Not Attended', 'excused':'Excused'}.get(
                    reg.attendance_record.status if reg.attendance_record else '', 'Unrecorded')])
    output = io.BytesIO()
    if format == 'csv':
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([[csv_safe(v) for v in row] for row in values])
        if roster:
            writer.writerow([])
            writer.writerow(roster_headers)
            writer.writerows([[csv_safe(v) for v in row] for row in roster])
        output.write(stream.getvalue().encode('utf-8-sig'))
    elif format == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.chart import BarChart, Reference
        book = Workbook()
        sheet = book.active
        sheet.title = 'Activities'
        sheet.append(headers)
        for row in values:
            sheet.append([csv_safe(v) for v in row])
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 26
        sheet.freeze_panes = 'A2'
        if roster:
            roster_sheet = book.create_sheet('Named attendance')
            roster_sheet.append(roster_headers)
            for row in roster:
                roster_sheet.append([csv_safe(v) for v in row])
            roster_sheet.freeze_panes = 'A2'
            for column in roster_sheet.columns:
                roster_sheet.column_dimensions[column[0].column_letter].width = 28
        chart_sheet = book.create_sheet('Campus accomplishments')
        chart_sheet.append(['Campus', 'Conducted activities'])
        for row in data['campus_chart']:
            chart_sheet.append([row['name'], row['count']])
        if data['campus_chart']:
            chart = BarChart()
            chart.type = 'bar'
            chart.title = 'Conducted activities · ' + data['period_label']
            chart.add_data(Reference(chart_sheet, min_col=2, min_row=1, max_row=chart_sheet.max_row), titles_from_data=True)
            chart.set_categories(Reference(chart_sheet, min_col=1, min_row=2, max_row=chart_sheet.max_row))
            chart_sheet.add_chart(chart, 'D2')
        from openpyxl.chart import LineChart
        trend = book.create_sheet('Delivery trend'); trend.append(['Period','Conducted activities'])
        for label,count in zip(data['month_labels'],data['monthly']):
            trend.append([label,count])
        if data['monthly']:
            line=LineChart(); line.title='Activity delivery over time'
            line.add_data(Reference(trend,min_col=2,min_row=1,max_row=trend.max_row),titles_from_data=True)
            line.set_categories(Reference(trend,min_col=1,min_row=2,max_row=trend.max_row)); trend.add_chart(line,'D2')
        scope_sheet=book.create_sheet('Scope'); scope_sheet.append([data['period_label']]); scope_sheet.append([csv_safe(data['scope_label'])]); scope_sheet.append(['Participant filters affect participant counts; pending recording is not absence.'])
        book.save(output)
    else:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from xml.sax.saxutils import escape
        from matplotlib.figure import Figure
        styles = getSampleStyleSheet()
        content = [Paragraph('PSU Volunteer Hub · Activity accomplishments', styles['Title']),
                   Paragraph(escape(data['period_label']), styles['Normal']),Paragraph(escape(data['scope_label']),styles['Normal']), Spacer(1, 12)]
        fig = Figure(figsize=(9, 3), layout='constrained')
        ax = fig.subplots()
        ax.barh([r['name'] for r in data['campus_chart']], [r['count'] for r in data['campus_chart']], color='#00408b')
        ax.set_xlabel('Conducted activities')
        image = io.BytesIO()
        fig.savefig(image, format='png', dpi=120)
        image.seek(0)
        content.append(Image(image, width=600, height=200))
        table = Table([[Paragraph(escape(str(v)), styles['Normal']) for v in row] for row in [[*headers[:7]], *[row[:7] for row in values]]], repeatRows=1, colWidths=[150, 70, 100, 100, 65, 55, 80])
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eff8')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
        content.append(table)
        content.extend([Spacer(1,16),Paragraph('Registrations, attendance, and numeric targets',styles['Heading2']),
            Paragraph('Rates and target outcomes remain pending until attendance recording is complete. Completed participation derives from recorded presence after the event ends.',styles['Normal'])])
        supplemental=Table([[Paragraph(escape(str(v)),styles['Normal']) for v in row] for row in
            [['Activity',*supplemental_headers],*[[r['event'].title,*extra] for r,extra in zip(data['rows'],supplemental_values)]]],
            repeatRows=1,colWidths=[145,55,45,45,55,60,65,65,65,80])
        supplemental.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        content.append(supplemental)
        trend_fig=Figure(figsize=(9,2.6),layout='constrained'); trend_ax=trend_fig.subplots()
        trend_ax.plot(data['month_labels'],data['monthly'],color='#00408b',marker='o'); trend_ax.set_ylabel('Conducted activities')
        trend_ax.tick_params(axis='x',rotation=45,labelsize=7)
        trend_image=io.BytesIO(); trend_fig.savefig(trend_image,format='png',dpi=110); trend_image.seek(0)
        content.extend([Spacer(1,12),Paragraph('Delivery trend',styles['Heading2']),Image(trend_image,width=650,height=188)])
        if data['event_id'] and data['rows']:
            event = data['rows'][0]['event']
            content.extend([Spacer(1, 14), Paragraph('Activity details', styles['Heading2']),
                Paragraph(escape(event.description), styles['Normal']),
                Paragraph('Location: ' + escape(event.location or 'Not recorded'), styles['Normal']),
                Paragraph('End: ' + escape(str(event.end_date or 'Not recorded')), styles['Normal'])])
        if roster:
            content.extend([Spacer(1, 14), Paragraph('Named attendance', styles['Heading2'])])
            roster_table = Table([[Paragraph(escape(str(v)), styles['Normal']) for v in row]
                for row in [roster_headers, *roster]], repeatRows=1, colWidths=[240, 100, 100, 180])
            roster_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff8')),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
            content.append(roster_table)
        SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=30, rightMargin=30).build(content)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f'psu-report-{data["year"]}.{format}',
        mimetype={'csv': 'text/csv', 'pdf': 'application/pdf', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}[format])


def export_aop(data, format):
    from app.reports import csv_safe
    goals = [row for row in data['goals']['rows'] if 'AOP' in row['plan_types']]
    headers = ['Indicator', 'Unit', 'Target', 'Verified actual', 'Status', 'Responsible office']
    rows = [[row['name'], row['unit'], float(row['target']),
             float(row['actual']) if row['verified'] else None, row['status'], row['responsible_office']] for row in goals]
    campus_headers = ['Campus', 'Obligations achieved', 'Total obligations', 'AOP achieved / total', 'ASP achieved / total', 'Pending evidence']
    campus_values = [[campus['campus'], campus['met'], campus['total'],
                      f"{campus['plans']['AOP']['met']} / {campus['plans']['AOP']['total']}",
                      f"{campus['plans']['ASP']['met']} / {campus['plans']['ASP']['total']}", campus['pending']]
                     for campus in data['campus_goals']]
    groups = {}
    for row in goals:
        if row['verified']:
            groups.setdefault(row['unit'], []).append(row)
    output = io.BytesIO()
    if format == 'csv':
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([[csv_safe(value) for value in row] for row in rows])
        if campus_values:
            writer.writerow([])
            writer.writerow(campus_headers)
            writer.writerows([[csv_safe(value) for value in row] for row in campus_values])
        output.write(stream.getvalue().encode('utf-8-sig'))
    elif format == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.chart import BarChart, Reference
        book = Workbook()
        sheet = book.active
        sheet.title = 'Annual Operational Plan'
        sheet.append(headers)
        for row in rows:
            sheet.append([csv_safe(value) for value in row])
        sheet.freeze_panes = 'A2'
        if campus_values:
            campus_sheet = book.create_sheet('Campus obligations')
            campus_sheet.append(campus_headers)
            for values in campus_values:
                campus_sheet.append([csv_safe(value) for value in values])
        for column in sheet.columns:
            sheet.column_dimensions[column[0].column_letter].width = 30
        for index, (unit, group) in enumerate(groups.items()):
            chart_sheet = book.create_sheet(f'Comparison {index + 1}')
            chart_sheet.append(['Indicator', 'Target', 'Verified actual'])
            for row in group:
                chart_sheet.append([csv_safe(row['name']), float(row['target']), float(row['actual'])])
            chart = BarChart()
            chart.type = 'bar'
            chart.title = unit
            chart.add_data(Reference(chart_sheet, min_col=2, max_col=3, min_row=1, max_row=chart_sheet.max_row), titles_from_data=True)
            chart.set_categories(Reference(chart_sheet, min_col=1, min_row=2, max_row=chart_sheet.max_row))
            chart_sheet.add_chart(chart, 'E2')
        book.save(output)
    else:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import A4, landscape
        from matplotlib.figure import Figure
        from xml.sax.saxutils import escape
        styles = getSampleStyleSheet()
        content = [Paragraph(f'PSU · Annual Operational Plan · {data["year"]}', styles['Title']),
            Paragraph('Annual approved targets and verified evidence. Pending evidence remains unknown.', styles['Normal']), Spacer(1, 14)]
        table = Table([[Paragraph(escape(str(value if value is not None else 'Evidence pending')), styles['Normal'])
                       for value in row] for row in [headers, *rows]], repeatRows=1, colWidths=[190, 80, 70, 80, 110, 100])
        content.append(table)
        if campus_values:
            content.extend([Spacer(1,14),Paragraph('Campus obligations, separate from university targets',styles['Heading2']),
                Table([[Paragraph(escape(str(value)),styles['Normal']) for value in values]
                       for values in [campus_headers,*campus_values]],repeatRows=1,colWidths=[180,90,90,100,100,90])])
        for unit, group in groups.items():
            # Split long comparisons so labels remain legible on paper.
            for offset in range(0, len(group), 6):
                selected = group[offset:offset + 6]
                fig = Figure(figsize=(9, 3.5), layout='constrained')
                ax = fig.subplots()
                positions = list(range(len(selected)))
                ax.barh([p - .2 for p in positions], [float(row['target']) for row in selected], height=.35, label='Target', color='#66758a')
                ax.barh([p + .2 for p in positions], [float(row['actual']) for row in selected], height=.35, label='Verified actual', color='#00408b')
                ax.set_yticks(positions, [row['name'][:45] for row in selected])
                ax.set_xlabel(unit)
                ax.legend()
                image = io.BytesIO()
                fig.savefig(image, format='png', dpi=120)
                image.seek(0)
                content.extend([Spacer(1, 14), Image(image, width=650, height=250)])
        SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=30, rightMargin=30).build(content)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f'psu-aop-{data["year"]}.{format}')


@workspace_bp.route('/imports')
@login_required
@roles_required('director', 'admin')
def imports():
    return render_template('workspace/imports.html')


@workspace_bp.route('/about')
def about():
    return render_template('workspace/about.html')


@workspace_bp.route('/activities/<int:event_id>/documents')
@login_required
@role_required('coordinator')
def activity_documents(event_id):
    return render_template('workspace/documents.html', event=owned_event(event_id))


@workspace_bp.route('/imports/<kind>', methods=['GET', 'POST'])
@login_required
@roles_required('director', 'admin')
def import_dataset(kind):
    if kind not in ('historical', 'annual'):
        abort(404)
    import secrets
    import hashlib
    import click
    from flask import session
    errors = []
    preview = token = None
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'import-previews'
    folder.mkdir(parents=True, exist_ok=True)
    if request.method == 'POST':
        slot = 'import_preview_' + kind
        try:
            if request.form.get('action') == 'confirm':
                staged = session.get(slot)
                if not staged or not secrets.compare_digest(staged['token'], request.form.get('token', '')):
                    abort(400)
                path = folder / Path(staged['file']).name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != staged['hash']:
                    abort(400)
                run_import(kind, path, False)
                path.unlink()
                session.pop(slot, None)
                flash('Import completed using the validated file.', 'success')
                return redirect(url_for('workspace.imports'))
            upload = request.files.get('dataset')
            if not upload or not upload.filename.lower().endswith('.csv'):
                raise ValueError('Choose a CSV file.')
            content = upload.read(2 * 1024 * 1024 + 1)
            if len(content) > 2 * 1024 * 1024:
                raise ValueError('Import files must be 2 MB or smaller.')
            path = folder / (secrets.token_hex(24) + '.csv')
            path.write_bytes(content)
            preview = run_import(kind, path, True)
            token = secrets.token_urlsafe(32)
            session[slot] = {'token': token, 'file': path.name, 'hash': hashlib.sha256(content).hexdigest()}
        except (ValueError, UnicodeError, click.ClickException) as exc:
            db.session.rollback()
            errors.append(str(exc))
    return render_template('workspace/import_dataset.html', kind=kind, preview=preview, token=token, errors=errors)


def run_import(kind, path, dry_run):
    if kind == 'annual':
        from app.annual_import import import_file
        from app.reports import ReportError
        try:
            created, unchanged = import_file(path, dry_run=dry_run)
            return f'{created} records to create; {unchanged} unchanged. Approved definitions remain immutable.'
        except ReportError as exc:
            raise ValueError(str(exc)) from exc
    import click
    from app.commands import import_historical_activities
    from contextlib import redirect_stdout
    buffer = io.StringIO()
    with click.Context(import_historical_activities) as context, redirect_stdout(buffer):
        context.invoke(import_historical_activities, csv_path=path, dry_run=dry_run)
    return buffer.getvalue()


@workspace_bp.route('/registrations')
@login_required
@role_required('volunteer')
def registrations():
    query = Registration.query.filter_by(user_id=current_user.id).join(Event)
    search = request.args.get('q', '').strip()[:200]
    if search:
        query = query.filter(Event.title.icontains(search, autoescape=True))
    campus = request.args.get('campus',type=int)
    if campus:
        query = query.filter(Event.campus_id == campus)
    category = request.args.get('category','')
    if category:
        query = query.filter(Event.category == category)
    if request.args.get('start_date') or request.args.get('end_date'):
        from app.reports import parse_date_range, ReportError
        try:
            start,end = parse_date_range(request.args.get('start_date'),request.args.get('end_date'))
            if start:
                query = query.filter(Event.date >= start)
            if end:
                from datetime import timedelta
                query = query.filter(Event.date < end + timedelta(days=1))
        except (ReportError, OverflowError) as exc:
            abort(400,description=str(exc))
    status = request.args.get('status', '')
    if status:
        if status not in ('pending', 'confirmed', 'completed', 'cancelled'):
            abort(400)
        query = query.filter(Registration.status == status)
    query = query.order_by(Registration.registered_at.desc(), Registration.id.desc())
    pagination = db.paginate(query.statement, per_page=15, max_per_page=15, error_out=False)
    categories = [r[0] for r in db.session.query(Event.category).join(Registration).filter(
        Registration.user_id == current_user.id,Event.category.isnot(None)).distinct().order_by(Event.category)]
    return render_template('workspace/registrations.html', pagination=pagination,
                           categories=categories,campuses=Campus.query.order_by(Campus.name).all())


@workspace_bp.route('/registrations/<int:registration_id>')
@login_required
@role_required('volunteer')
def registration(registration_id):
    row = Registration.query.filter_by(id=registration_id, user_id=current_user.id).first_or_404()
    from app.routes.events import _cancellation_state
    state = _cancellation_state(row)
    return render_template('workspace/registration.html', registration=row, can_withdraw=state['can_request'],
                           withdrawal=state,now=local_now())


@workspace_bp.route('/management')
@login_required
@roles_required('director', 'admin')
def management():
    return render_template('workspace/management.html')


@workspace_bp.route('/categories')
@login_required
@roles_required('director', 'admin')
def categories():
    from app.models.event import ActivityCategory
    return render_template('workspace/categories.html', categories=ActivityCategory.query.order_by(ActivityCategory.name).all())


@workspace_bp.route('/volunteers')
@login_required
@roles_required('coordinator', 'director', 'admin')
def volunteers():
    query = User.query.filter_by(role='volunteer')
    campus_id = current_user.campus_id if current_user.role == 'coordinator' else request.args.get('campus_id', type=int)
    if current_user.role == 'coordinator' and not campus_id:
        abort(403)
    if campus_id:
        query = query.filter_by(campus_id=campus_id)
    search = request.args.get('q', '').strip()[:200]
    if search:
        query = query.filter(or_(User.name.icontains(search, autoescape=True), User.email.icontains(search, autoescape=True)))
    pagination = db.paginate(query.order_by(User.name, User.id).statement, per_page=25, max_per_page=25, error_out=False)
    return render_template('workspace/volunteers.html', pagination=pagination)


@workspace_bp.route('/reports/historical')
@login_required
@roles_required('coordinator', 'director', 'admin')
def historical():
    from app.services.historical_reports import historical_scope
    query, chart, types = historical_scope(request.args,current_user)
    pagination = db.paginate(query.statement,per_page=25,max_per_page=25,error_out=False)
    return render_template('workspace/historical.html',pagination=pagination,historical_chart=chart,
                           activity_types=types,campuses=Campus.query.order_by(Campus.name).all())


@workspace_bp.route('/reports/historical/export/<format>')
@login_required
@roles_required('coordinator','director','admin')
def historical_export(format):
    from app.services.historical_reports import export_historical
    return export_historical(format,request.args,current_user)


@workspace_bp.route('/activities/<int:event_id>/registrations')
@login_required
@roles_required('coordinator', 'director', 'admin')
def activity_registrations(event_id):
    event = owned_event(event_id)
    query = Registration.query.filter_by(event_id=event.id)
    search = request.args.get('q', '').strip()[:200]
    if search:
        query = query.filter(or_(Registration.user.has(or_(User.name.icontains(search, autoescape=True),
            User.email.icontains(search, autoescape=True))), Registration.external_participant.has(
            or_(ExternalParticipant.name.icontains(search, autoescape=True), ExternalParticipant.email.icontains(search, autoescape=True)))))
    status = request.args.get('status', '')
    if status in ('pending', 'confirmed', 'completed', 'cancelled'):
        query = query.filter(Registration.status == status)
    elif status:
        abort(400)
    query = query.order_by(Registration.registered_at.desc(), Registration.id)
    pagination = db.paginate(query.statement, per_page=25, max_per_page=25, error_out=False)
    invited = User.query.filter(User.id.in_((event.audience or {}).get('volunteer_ids', []))).order_by(User.name).all()
    return render_template('workspace/activity_registrations.html', event=event, pagination=pagination, invited=invited)
