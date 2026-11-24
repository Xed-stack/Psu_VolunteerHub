"""Explicit, empty-target provisioning for the 2026 Railway presentation year."""
import hashlib
import json
import os
import random
import shutil
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe

import click
from flask import current_app
from flask.cli import with_appcontext
from flask_login import login_user
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from werkzeug.datastructures import MultiDict

from app.campuses import PSU_CAMPUSES, campus_affiliations
from app.demo_dataset import ACTIVITIES, FIRST_NAMES, LAST_NAMES
from app.models import db
from app.models.annual_plan import (AnnualActivityMapping, AnnualGoalProposal,
                                   AnnualIndicator, AnnualPlan, AnnualTarget)
from app.models.audit import AuditLog
from app.models.event import (Attendance, CancellationRequest, Campus, Event,
                              EventAnnouncement, ExternalParticipant, Milestone,
                              Registration, SdgGoal)
from app.models.notification import Notification
from app.models.policy import (ParticipationAgreementRevision, PrivacyAcknowledgement,
                               PrivacyRevision, TermsAcceptance, TermsRevision)
from app.models.user import (Interest, Skill, SystemSetting, User, VolunteerProfile,
                             user_interests, user_skills)
from app.models.workspace import (ActivityProposal, ExternalGroup, FormDraft,
                                  PartnerAgency, PartnerAgreement)
from app.services.activity_workflow import local_now


VERSION = 'railway-year-2026-v1'
MARKER = 'railway_year_manifest'
DEFAULT_EMAILS = ('admin@psu.edu', 'director@psu.edu', 'coordinator@psu.edu', 'student@psu.edu')
CAMPUS_ORDER = ('LINGAYEN', 'URDANETA', 'BAYAMBANG', 'SANCARLOS', 'BINMALEY',
                'STAMARIA', 'ASINGAN', 'INFANTA', 'ALAMINOS')
COPY_MODELS = (User, VolunteerProfile, TermsRevision, PrivacyRevision,
               ParticipationAgreementRevision, TermsAcceptance, PrivacyAcknowledgement)
GOAL_NAMES = (
    'Community Reading Partnerships', 'Coastal Habitat Stewardship', 'Household Wellness Education',
    'Digital Skills for Community Learners', 'Community Food Gardens', 'Barangay Disaster Readiness',
    'Local Heritage Learning', 'Youth Recreation and Wellbeing', 'Riverbank Restoration',
    'Numeracy Learning Support', 'Household Food Security', 'Accessible Digital Services',
    'Family Literacy Circles', 'Community Waste Reduction', 'Nutrition and Healthy Habits',
    'Small Enterprise Digital Records', 'Sustainable Backyard Production', 'First Aid Readiness',
    'Community Arts Workshops', 'Inclusive Youth Sports', 'Watershed Care',
    'School Learning Resource Support', 'Responsible Food Handling', 'Online Services Assistance',
    'Community Livelihood Learning',
)


def require(condition, message):
    if not condition:
        raise click.ClickException(message)


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _target(database):
    require(database == db.engine.url.database, 'Exact destination database name does not match.')
    require(current_app.config.get('MAIL_SUPPRESS_SEND') is True,
            'Set MAIL_SUPPRESS_SEND=true on the destination app, including its web workers.')
    if not current_app.testing:
        require(current_app.config.get('APP_ENV') == 'production', 'Use the production Flask entry point.')
        require(db.engine.dialect.name in ('mysql', 'mariadb'), 'Railway destination must use MySQL/MariaDB.')
        require(os.environ.get('RAILWAY_SERVICE_ID') and
                os.environ.get('RAILWAY_SERVICE_ID') == os.environ.get('RAILWAY_SEED_SERVICE_ID'),
                'RAILWAY_SEED_SERVICE_ID must match the independently verified new app service.')
        require(os.environ.get('RAILWAY_SEED_DATABASE_HOST') and
                db.engine.url.host == os.environ.get('RAILWAY_SEED_DATABASE_HOST'),
                'RAILWAY_SEED_DATABASE_HOST must match the independently verified new database host.')
    require(not inspect(db.engine).get_view_names(), 'Destination contains views; use a new empty database.')


def _source_accounts():
    """Read a consistent snapshot; never start the source Flask app or run its hooks."""
    url = os.environ.get('RAILWAY_SEED_SOURCE_DATABASE_URL')
    require(url, 'Set the private RAILWAY_SEED_SOURCE_DATABASE_URL for the existing demo database.')
    source = create_engine(url, hide_parameters=True)
    try:
        require(source.url != db.engine.url, 'Source and destination must be different databases.')
        if not current_app.testing:
            require(source.dialect.name in ('mysql', 'mariadb') and
                    os.environ.get('RAILWAY_SEED_SOURCE_HOST') and
                    source.url.host == os.environ.get('RAILWAY_SEED_SOURCE_HOST'),
                    'Verify RAILWAY_SEED_SOURCE_HOST against the existing demo MySQL service.')
            require((source.url.host, source.url.port, source.url.database) !=
                    (db.engine.url.host, db.engine.url.port, db.engine.url.database),
                    'Source and destination resolve to the same configured database.')
        metadata = MetaData()
        with source.connect() as connection:
            if source.dialect.name in ('mysql', 'mariadb'):
                connection.exec_driver_sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                connection.exec_driver_sql('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
            def rows(name, predicate=None):
                table = Table(name, metadata, autoload_with=connection)
                query = select(table)
                if predicate:
                    query = query.where(predicate(table))
                return [dict(row) for row in connection.execute(query).mappings()]
            users = rows('users', lambda t: t.c.email.in_(DEFAULT_EMAILS))
            require({u['email'] for u in users} == set(DEFAULT_EMAILS), 'Source must contain all four default accounts.')
            ids = [u['id'] for u in users]
            require(all(u['is_active'] and u['password_hash'] for u in users), 'Default accounts must be active with existing password hashes.')
            # Older demo snapshots used an ``admin`` role.  The destination
            # schema intentionally has only director/coordinator/volunteer;
            # translate that one legacy role while leaving the source read-only.
            roles = {'admin@psu.edu': {'admin', 'director'}, 'director@psu.edu': {'director'},
                     'coordinator@psu.edu': {'coordinator'}, 'student@psu.edu': {'volunteer'}}
            require(all(u['role'] in roles[u['email']] for u in users),
                    'Default roles do not match the current three-role schema. Review source upgrades first; no roles were changed.')
            snapshot = {'users': users, 'campuses': rows('campuses')}
            for model in COPY_MODELS[1:]:
                name = model.__tablename__
                snapshot[name] = rows(name, (lambda t: t.c.user_id.in_(ids)) if 'user_id' in model.__table__.c else None)
            for table in (user_interests, user_skills):
                snapshot[table.name] = rows(table.name, lambda t: t.c.user_id.in_(ids))
            snapshot['interests'] = rows('interests')
            snapshot['skills'] = rows('skills')
            connection.rollback()
        source_campuses = {c['id']: c for c in snapshot['campuses']}
        require(all(u['campus_id'] in source_campuses for u in users if u['role'] in ('volunteer', 'coordinator')),
                'Default volunteer and coordinator require existing official campuses.')
        require(all((source_campuses[u['campus_id']]['name'], source_campuses[u['campus_id']]['code']) in PSU_CAMPUSES
                    for u in users if u['campus_id'] is not None), 'A default account has an unsupported campus.')
        return snapshot
    finally:
        source.dispose()


def _copy_accounts(snapshot, campuses):
    source_campuses = {c['id']: c['code'] for c in snapshot['campuses']}
    users = {}
    for record in snapshot['users']:
        values = {c.name: record[c.name] for c in User.__table__.columns if c.name in record}
        if values['email'] == 'admin@psu.edu' and values.get('role') == 'admin':
            values['role'] = 'director'
        if values['campus_id'] is not None:
            values['campus_id'] = campuses[source_campuses[values['campus_id']]].id
        # Column name is is_active; the mapped Python attribute is _is_active.
        values['_is_active'] = values.pop('is_active')
        user = User(**values)
        db.session.add(user)
        users[user.email] = user
    db.session.flush()
    ids = {u.id for u in users.values()}
    for model in COPY_MODELS[1:]:
        for record in snapshot[model.__tablename__]:
            values = {c.name: record[c.name] for c in model.__table__.columns if c.name in record}
            if 'published_by_id' in values and values['published_by_id'] not in ids:
                values['published_by_id'] = None
            db.session.add(model(**values))
        db.session.flush()
    for table, model in ((user_interests, Interest), (user_skills, Skill)):
        names = {row['id']: row['name'] for row in snapshot[model.__tablename__]}
        foreign = 'interest_id' if model == Interest else 'skill_id'
        for record in snapshot[table.name]:
            item = model.query.filter_by(name=names[record[foreign]]).first()
            if item is None:
                item = model(name=names[record[foreign]])
                db.session.add(item)
                db.session.flush()
            db.session.execute(table.insert().values(user_id=record['user_id'], **{foreign: item.id}))
    db.session.flush()
    return users


def _profile_files(snapshot):
    files = {}
    for user in snapshot['users']:
        value = user.get('profile_image_path')
        if not value:
            continue
        relative = Path(value)
        require(relative.parts[:2] == ('uploads', 'profiles') and len(relative.parts) == 3,
                'Unsupported default profile image path; no files copied.')
        root = os.environ.get('RAILWAY_SEED_SOURCE_UPLOAD_FOLDER')
        require(root, 'Provide RAILWAY_SEED_SOURCE_UPLOAD_FOLDER with the default accounts\' existing profile photos.')
        source = Path(root).resolve() / 'profiles' / relative.name
        require(source.resolve().is_relative_to(Path(root).resolve()) and source.is_file(),
                'A default profile photo is missing from the protected source upload folder.')
        files['public/profiles/' + relative.name] = source
    return files


def _people(accounts, campuses, now):
    rng = random.Random(20261124)
    skills = {s.name: s for s in Skill.query.all()}
    interests = {i.name: i for i in Interest.query.all()}
    volunteers, coordinators = {}, {}
    # One expensive hash, with no disclosed password; generated accounts are not default logins.
    disabled = User()
    disabled.set_password(token_urlsafe(48))
    student = accounts['student@psu.edu']
    staff = accounts['coordinator@psu.edu']
    joined = datetime(2025, 9, 1, 9)
    def person(index, role, campus):
        name = f'{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[index // len(FIRST_NAMES) % len(LAST_NAMES)]}'
        user = User(name=name, email=f'{role}.{index:04d}@people.invalid',
                    id_number=f'2026-{index:05d}', role=role, campus=campus,
                    volunteer_type=('student', 'faculty', 'staff')[index % 3],
                    sex=rng.choices(['female', 'male', 'prefer_not_to_say'], [52, 43, 5])[0],
                    college_affiliation=rng.choice(campus_affiliations(campus)),
                    password_hash=disabled.password_hash, created_at=joined + timedelta(days=index % 100),
                    first_use_guide_dismissed_at=joined + timedelta(days=110))
        db.session.add(user)
        if role == 'volunteer':
            user.profile = VolunteerProfile(past_participation=[])
            category = ACTIVITIES[index % len(ACTIVITIES)][1]
            user.interests = [interests[category]]
            user.skills = [skills[n] for n in current_app.config['INTEREST_SKILL_MAP'][category]]
        return user
    for ci, campus in enumerate(campuses.values()):
        coordinators[campus.id] = staff if staff.campus_id == campus.id else person(800 + ci, 'coordinator', campus)
        volunteers[campus.id] = [student] if student.campus_id == campus.id else []
        while len(volunteers[campus.id]) < 20:
            index = ci * 20 + len(volunteers[campus.id])
            volunteers[campus.id].append(person(index, 'volunteer', campus))
    db.session.flush()
    external = {}
    for ci, campus in enumerate(campuses.values()):
        external[campus.id] = []
        for j in range(10):
            index = ci * 10 + j
            person_record = ExternalParticipant(id_number=f'CP-2026-{index+1:04d}',
                name=f'{FIRST_NAMES[(index+9) % 25]} {LAST_NAMES[(index//25+17) % len(LAST_NAMES)]}',
                email=f'community.{index+1:04d}@people.invalid',
                sex=rng.choices(['female', 'male', 'prefer_not_to_say', None], [48, 44, 5, 3])[0],
                address=f'{campus.name}, Pangasinan', created_at=joined)
            db.session.add(person_record)
            external[campus.id].append(person_record)
    db.session.flush()
    return volunteers, coordinators, external


def _pdf(folder, filename, title, lines):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from xml.sax.saxutils import escape
    path = folder / 'private' / 'proposals' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles['Title'].alignment = TA_LEFT
    styles['Title'].textColor = colors.HexColor('#15385b')
    content = [Paragraph('PSU Volunteer Hub', styles['Heading2']), Paragraph(escape(title), styles['Title']), Spacer(1, 16)]
    for line in lines:
        content.extend([Paragraph(escape(str(line)), styles['BodyText']), Spacer(1, 10)])
    SimpleDocTemplate(str(path), rightMargin=48, leftMargin=48, topMargin=48,
                      bottomMargin=48, title=title).build(content)
    return {'path': filename, 'name': filename, 'readable': True}


def _activities(folder, campuses, volunteers, coordinators, external, now):
    rng = random.Random(9182026)
    sdgs = {s.number: s for s in SdgGoal.query.all()}
    groups = {}
    future_index = 0
    future_end = datetime(2026, 12, 30, 9)
    for ci, campus in enumerate(campuses.values()):
        coordinator = coordinators[campus.id]
        agencies = []
        for k, kind in enumerate(('Community Learning Council', 'Livelihood Resource Network')):
            agency = PartnerAgency(campus_id=campus.id, name=f'{campus.name} {kind}',
                contact_name=f'{FIRST_NAMES[(ci*2+k+6)%25]} {LAST_NAMES[ci+8]}',
                email=f'partner.{ci+1}.{k+1}@people.invalid')
            db.session.add(agency)
            agencies.append(agency)
        db.session.flush()
        moa = _pdf(folder, f'moa-2026-{ci+1:02d}.pdf', f'{campus.name} Community Partnership Agreement',
                   ['Reference: MOA-2026-' + f'{ci+1:02d}', 'Validity: 01 January through 31 December 2026.',
                    f'Partners: PSU {campus.name} and {agencies[0].name}.',
                    'Coordinate community learning, safeguarding, venue preparation and participant support.',
                    'Each party designates a coordinator and reviews implementation after every activity.'])
        agreement = PartnerAgreement(agency_id=agencies[0].id, reference=f'MOA-2026-{ci+1:02d}',
            valid_from=date(2026, 1, 1), valid_until=date(2026, 12, 31), document=moa)
        db.session.add(agreement)
        db.session.flush()
        groups[campus.id] = []
        # 8+8+7*7=65 ended; 2 ongoing; 15 future; 4 drafts; 4 cancelled.
        states = ['ended'] * (8 if ci < 2 else 7)
        if ci < 2:
            states += ['ongoing', 'future']
        elif ci == 2:
            states += ['future'] * 3
        elif ci < 5:
            states += ['future', 'future', 'draft']
        else:
            states += ['future', 'cancelled', 'draft' if ci in (5, 6) else 'future']
        for j, state in enumerate(states):
            if state == 'ended':
                jan = datetime(2026, 1, 15+ci, 8)
                ended_count = 8 if ci < 2 else 7
                start = jan + (now - timedelta(days=2+ci%3) - jan) * (j / (ended_count-1))
                start = start.replace(hour=8 + j % 3, minute=0, second=0, microsecond=0)
            elif state == 'ongoing':
                start = now - timedelta(minutes=45)
            else:
                start = now + timedelta(days=1) + (future_end - now - timedelta(days=1)) * (future_index / 23)
                start = start.replace(hour=9, minute=0, second=0, microsecond=0)
                future_index += 1
            title, category, goals = ACTIVITIES[(ci*3+j) % len(ACTIVITIES)]
            event = Event(title=f'{title}: {campus.name} Session {j+1}',
                description=f'{campus.name} volunteers work with community facilitators on {title.lower()}. '
                            'The programme includes a safety briefing, guided practice, small-group support and a closing review.',
                campus=campus, created_by=coordinator, date=start, end_date=start+timedelta(hours=4),
                cancellation_deadline=start-timedelta(days=1), category=category,
                location=f'{campus.name} community learning centre', slots=40,
                target_participants=28 if j % 4 == 0 else 18,
                conducting_department=campus_affiliations(campus)[j % len(campus_affiliations(campus))],
                participant_type='Students, faculty, staff and community participants',
                audience={'departments': campus_affiliations(campus)},
                agreement_id=agreement.id, participation_agreement_text='Follow the safety briefing, respect community members and protect participant information.',
                participation_agreement_version='2026-01', lifecycle_status=state if state in ('draft', 'cancelled') else 'approved',
                cancellation_reason='Venue repairs require rescheduling with the community partner.' if state == 'cancelled' else None,
                cancelled_at=now-timedelta(days=1) if state == 'cancelled' else None)
            db.session.add(event)
            event.sdgs = [sdgs[n] for n in sorted(set((*goals, 17)))]
            event.required_skills_rel = Skill.query.filter(Skill.name.in_(current_app.config['INTEREST_SKILL_MAP'][category])).all()
            event.proposal_document = _pdf(folder, f'proposal-2026-{ci+1:02d}-{j+1:02d}.pdf', event.title,
                [f'Campus: {campus.name}', f'Department: {event.conducting_department}',
                 f'Schedule: {start:%d %B %Y %H:%M} to {event.end_date:%H:%M}, Philippine time.',
                 f'Venue: {event.location}', f'Participant target: {event.target_participants}',
                 'Objective: strengthen practical community skills through facilitated learning and volunteer support.',
                 'Implementation: orientation, guided learning stations, practical exercises and participant feedback.',
                 f'Primary partner: {agencies[0].name}', 'Coordination: campus extension office.'])
            db.session.add(event)
            db.session.flush()
            groups[campus.id].append(event)
            from app.services.proposal_record import CHOICES, normalize_record, validate_record
            content = dict(implementing_unit=event.conducting_department,
                rationale='Community consultations identified a need for accessible practical learning and sustained volunteer support.',
                general_objectives='Improve access to community learning and practical support.',
                specific_objectives='Deliver guided practice, document participation and gather feedback for follow-up sessions.',
                methodology='Orientation, small-group learning stations, supervised practice and a closing reflection.',
                beneficiary_count='30', volunteer_count='20', budget_na='yes',
                budget_reason='Existing campus learning materials and partner-provided venue are used.',
                evaluation='Review attendance, facilitator observations and participant feedback.',
                sustainability='Coordinate follow-up learning sessions with the community council.',
                conclusion='Consolidate lessons and identify the next community learning priorities.',
                partnership_status='existing', agency_id=str(agencies[0].id),
                additional_agency_ids=[str(agencies[1].id)],
                psu_roles='Provide facilitators, learning materials and participant safeguarding.',
                partner_roles='Coordinate venue access and community participation.',
                partnership_duration='01 January through 31 December 2026',
                team=[dict(name=coordinator.name, designation='Campus Extension Coordinator', campus=campus.name, role='Leader')],
                implementation=[dict(activity=title, people='Campus volunteers and community facilitators',
                    timeline=f'{start:%d %B %Y}', output='Guided practice and participant feedback')],
                risks=[dict(risk='Severe weather or venue interruption', impact='Moderate',
                    mitigation='Confirm venue arrangements and communicate schedule changes before travel.')])
            content.update({key:[values[(ci+j)%len(values)]] for key,values in CHOICES.items()})
            content['beneficiary_groups']=['Youth and Students (5–19 years old)']
            content['volunteer_groups']=['Students']
            content=normalize_record(content)
            require(not validate_record(content), 'Generated proposal does not pass the existing proposal validator.')
            db.session.add(ActivityProposal(event=event, agency_id=agencies[0].id, content=content,
                capture={'method':'manual'}, publishing_snapshot={} if state == 'draft' else
                {'Activity Title':[event.title], 'Public Activity Description':[event.description],
                 'Start (Philippine Time)':[event.date.isoformat(timespec='minutes')],
                 'End (Philippine Time)':[event.end_date.isoformat(timespec='minutes')],
                 'Location':[event.location], 'Category':[category],
                 'Volunteer Registration Slots':[str(event.slots)], 'Total Participant Target':[str(event.target_participants)],
                 'Conducting Department':[event.conducting_department], 'Type of Participants':[event.participant_type],
                 'Audience Departments':campus_affiliations(campus),
                 'Primary Agency':[agencies[0].name], 'Additional Partner Agencies':[agencies[1].name],
                 'Signed MOA':[agreement.reference], 'AOP Goals':[],
                 'Required Skills':[s.name for s in event.required_skills_rel],
                 'Sustainable Development Goals':[f'SDG {s.number} {s.name}' for s in event.sdgs]}))
            if state == 'draft':
                db.session.add(FormDraft(user_id=coordinator.id, campus_id=campus.id,
                    key=f'activity:{event.id}', payload=dict(title=[event.title], description=[event.description],
                        date=[event.date.isoformat(timespec='minutes')], end_date=[event.end_date.isoformat(timespec='minutes')],
                        location=[event.location], category=[category], slots=[str(event.slots)],
                        target_participants=[str(event.target_participants)], proposal_record=[json.dumps(content)],
                        _proposal=event.proposal_document), updated_at=now-timedelta(hours=3)))
                continue
            group = ExternalGroup(event_id=event.id, name=f'{campus.name} Community Participants')
            db.session.add(group)
            db.session.flush()
            selected = list(volunteers[campus.id])
            rng.shuffle(selected)
            # Keep the preserved student's involvement in every activity on their campus.
            selected.sort(key=lambda u: u.email != 'student@psu.edu')
            people = [(u, None) for u in selected[:16+j%5]] + [(None, external[campus.id][(j+k)%10]) for k in range(5)]
            for seat, (user, person) in enumerate(people):
                registered = min(start-timedelta(days=5+seat%8), now-timedelta(days=2))
                withdrew = state == 'cancelled' or seat == 3
                outcome = None
                if state in ('ended', 'ongoing') and not withdrew:
                    if not ((j % 5 == 0 or state == 'ongoing') and seat % 3 == 0):
                        outcome = 'absent' if seat % (2 if j % 4 == 1 else 9) == 0 else 'excused' if seat%13==0 else 'present'
                reg = Registration(event=event, user=user, external_participant=person,
                    status='cancelled' if withdrew else 'completed' if state=='ended' and outcome=='present' else 'confirmed',
                    registered_at=registered)
                # Synthetic consent belongs only to generated identities, never the retained accounts.
                if not user or user.email not in DEFAULT_EMAILS:
                    reg.policy_accepted_at, reg.policy_version = registered, '2026-01'
                if person:
                    if person.group_id is None:
                        person.group_id=group.id
                    reg.external_privacy_accepted_at, reg.external_privacy_version = registered, '2026-01'
                db.session.add(reg)
                if outcome:
                    db.session.add(Attendance(registration=reg, event=event, user_id=user.id if user else None, status=outcome))
                if user and seat in (0, 3, 5) and state != 'cancelled':
                    status = {0:'pending',3:'approved',5:'rejected'}[seat]
                    request_time = registered + timedelta(hours=2)
                    db.session.add(CancellationRequest(registration=reg, reason='Schedule Conflict',
                        details='An academic or household obligation overlaps the scheduled activity.', status=status,
                        requested_at=request_time, reviewed_at=None if status=='pending' else request_time+timedelta(hours=3),
                        reviewed_by_id=None if status=='pending' else coordinator.id,
                        review_note=None if status=='pending' else 'Reviewed against the activity schedule.'))
            db.session.add(EventAnnouncement(event=event, author_id=coordinator.id,
                announcement_type='cancelled_postponed' if state=='cancelled' else 'event_update',
                message=event.cancellation_reason if state=='cancelled' else 'Please review the venue details and bring water and the materials listed in the briefing.',
                created_at=min(start-timedelta(days=2), now-timedelta(days=1))))
            db.session.add(Notification(user_id=volunteers[campus.id][0].id, title='Activity Update',
                message=f'Please review the latest arrangements for {event.title}.', related_event_id=event.id,
                notification_type='event_update', created_at=min(start-timedelta(days=2), now-timedelta(days=1)), is_read=j%2==0))
            if state == 'ended' and j % 2 == 0:
                report = _pdf(folder, f'accomplishment-2026-{ci+1:02d}-{j+1:02d}.pdf', event.title+' - Accomplishment Record',
                    [f'Campus: {campus.name}', f'Activity date: {start:%d %B %Y}',
                     'Facilitators delivered the planned learning stations and collected participant feedback.',
                     'Attendance is recorded separately in the activity roster. Outstanding entries remain subject to review.',
                     'Next steps: consolidate feedback and confirm the next community session.'])
                db.session.add(Milestone(event=event, filename=report['name'], upload_path='proposals/'+report['path'],
                    category='report', uploaded_by_id=coordinator.id, uploaded_at=event.end_date+timedelta(hours=1)))
    db.session.flush()
    return groups


def _goals(campuses, coordinators, accounts, groups, now):
    plan = AnnualPlan(source_key='aop-2026', year=2026, plan_type='AOP', title='2026 Community Extension Programme',
        source_document='2026 Annual Operational Plan', approval_reference='AOP-2026-01', approval_date=date(2026,1,5),
        imported_at=datetime(2026,1,5,1))
    db.session.add(plan)
    director = accounts['director@psu.edu']
    expected = []
    for ci, campus in enumerate(campuses.values()):
        for j in range(3 if ci < 7 else 2):
            index = len(expected)
            rank = index*7 % 25
            state = 'not_started' if rank<5 else 'in_progress' if rank<15 else 'met' if rank<22 else 'above'
            target = 2 + index%3
            actual = 0 if state=='not_started' else target-1 if state=='in_progress' else target if state=='met' else target+1
            key=f'aop-2026-{index+1:02d}'
            indicator = AnnualIndicator(source_key=key, plan=plan, code=f'AOP-{index+1:02d}',
                program='Community Extension and Volunteer Development', name=GOAL_NAMES[index],
                definition=f'Deliver coordinated {GOAL_NAMES[index].lower()} activities with {campus.name} community partners.',
                unit='activities', responsible_office='University Extension Office', evidence_basis='activities')
            goal = AnnualTarget(source_key=key, indicator=indicator, target_value=target, workflow_kind='director_goal',
                start_date=date(2026,1,10), end_date=date(2026,12,31), deadline=date(2026,12,31))
            db.session.add(goal)
            db.session.flush()
            payload=dict(year=2026, title=indicator.name, description=indicator.definition, target_value=target,
                         start_date='2026-01-10', end_date='2026-12-31')
            published=datetime(2026,1,6,1)
            db.session.add(AnnualGoalProposal(workflow_kind='director_goal', proposed_by_id=director.id,
                published_target_id=goal.id, payload=payload, status='published', created_at=published-timedelta(days=1),
                submitted_at=published, history=[dict(action='published', actor=director.id, at=published.isoformat(), payload=payload)]))
            child = AnnualTarget(source_key=key+':'+campus.code, indicator=indicator, campus=campus,
                director_target_id=goal.id, workflow_kind='campus_commitment', target_value=target)
            db.session.add(child)
            db.session.flush()
            submitted=published+timedelta(days=1)
            commitment=dict(target_value=target, note='Campus sessions coordinated with community partners and academic departments.')
            history=[dict(action='commitment_submitted', actor=coordinators[campus.id].id,
                          at=submitted.isoformat(), payload=commitment)]
            if index%4==0:
                history.insert(0, dict(action='draft_saved', actor=coordinators[campus.id].id,
                    at=(submitted-timedelta(hours=4)).isoformat(), payload=dict(target_value=target+1)))
            proposal=AnnualGoalProposal(workflow_kind='campus_commitment', director_target_id=goal.id,
                campus_id=campus.id, proposed_by_id=coordinators[campus.id].id, published_target_id=child.id,
                payload=commitment, status='submitted', created_at=submitted-timedelta(hours=4), submitted_at=submitted, history=history)
            if index%6==0:
                history[0:0]=[dict(action='commitment_submitted', actor=coordinators[campus.id].id,
                    at=(submitted-timedelta(hours=6)).isoformat(), payload=dict(target_value=target+1))]
                child.version=2
                proposal.version=2
            db.session.add(proposal)
            ended=[e for e in groups[campus.id] if e.lifecycle_status=='approved' and e.end_date<now]
            offset=j % len(ended)
            selected=(ended[offset:]+ended[:offset])[:actual]
            selected += [e for e in groups[campus.id] if e.lifecycle_status=='approved' and e.end_date>now][:1]
            for event in selected:
                db.session.add(AnnualActivityMapping(target=child, event=event))
                linked=min(event.date-timedelta(days=2), now-timedelta(days=1))
                history.append(dict(action='activity_linked', actor=coordinators[campus.id].id,
                    at=linked.isoformat(), payload=dict(event_id=event.id)))
                record=event.proposal_record
                record.publishing_snapshot={**record.publishing_snapshot,
                    'AOP Goals':[*record.publishing_snapshot.get('AOP Goals',[]), indicator.name]}
            proposal.history=sorted(history, key=lambda entry:entry['at'])
            for recipient, title in ((coordinators[campus.id], 'AOP Goal Published'), (director, 'Campus Commitment Submitted')):
                db.session.add(Notification(user_id=recipient.id, title=title, message=indicator.name,
                    notification_type='aop_goal', created_at=submitted, is_read=index%3!=0))
            expected.append(dict(goal_id=goal.id, campus=campus.code, target=target, completed=actual, status=state))
    db.session.flush()
    return expected


def _reviews(accounts, now):
    from app.services.finding_reviews import generated, item_for, mutate
    from app.services.workspace_reports import workspace_report
    with current_app.test_request_context('/workspace/overview?year=2026&period=annual'):
        login_user(accounts['director@psu.edu'])
        data=workspace_report(Event.query, MultiDict({'year':'2026', 'period':'annual'}), accounts['director@psu.edu'], now)
        # Report findings are the same source used by both Overview review modes.
        findings=generated(data)
        require(findings, 'No real Needs Attention findings were generated.')
        for index, finding in enumerate(findings[:12]):
            item=item_for(finding, None)
            action='follow_up' if finding['can_follow_up'] and index%3==0 else 'close' if (
                index%3==1 and finding['snapshot']['code'] not in ('record_attendance','remaining_goals','no_targets')) else 'save'
            form=MultiDict(dict(revision=item['revision'], version=str(item['version']),
                assessment='Reviewed with the campus extension team; attendance and delivery evidence require separate consideration.',
                recommendation=''))
            if action=='close':
                form['closure_reason']='historical_outcome_reviewed'
            mutate(item, action, form)
        return dict(findings=dict(Counter(f['snapshot']['code'] for f in findings)),
                    sex_breakdown=data['sex_breakdown'])


def _dest_file(relative):
    kind, tail=relative.split('/',1)
    root=Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) if kind=='private' else Path(current_app.static_folder)/'uploads'
    path=root/Path(tail)
    require(path.resolve().is_relative_to(root.resolve()), 'File path escaped the destination upload directory.')
    return path


def _fingerprint():
    result={}
    for table in db.metadata.sorted_tables:
        query=select(table).order_by(*table.primary_key.columns)
        if table.name=='system_settings':
            query=query.where(table.c.key != MARKER)
        result[table.name]=_hash([dict(row) for row in db.session.execute(query).mappings()])
    return result


def _validate(expected, accounts, snapshot, now):
    from app.services.aop_goals import activity_state
    require(Event.query.count()==90 and User.query.filter_by(role='volunteer').count()==180 and
            User.query.filter_by(role='coordinator').count()==9 and ExternalParticipant.query.count()==90,
            'Seed account/activity counts differ from the specification.')
    counts=Counter('draft' if e.lifecycle_status=='draft' else 'cancelled' if e.lifecycle_status=='cancelled'
                   else 'ended' if e.end_date<=now else 'ongoing' if e.date<=now else 'future' for e in Event.query.all())
    require(counts==dict(ended=65, ongoing=2, future=15, draft=4, cancelled=4), 'Activity date/state totals differ from the specification.')
    require(len(expected)==25 and AnnualTarget.query.filter_by(workflow_kind='campus_commitment').count()==25,
            'Exactly 25 goals and 25 submitted campus commitments are required.')
    for row in expected:
        goal=db.session.get(AnnualTarget, row['goal_id'])
        child=AnnualTarget.query.filter_by(director_target_id=goal.id).one()
        actual=sum(activity_state(m.event, goal, now)=='Completed' for m in child.activity_mappings)
        require(actual==row['completed'], 'Derived AOP completion differs from its expected goal outcome.')
    for record in snapshot['users']:
        user=accounts[record['email']]
        for column in User.__table__.columns:
            if column.name in record and column.name!='campus_id':
                expected_value = record[column.name]
                if column.name == 'role' and record['email'] == 'admin@psu.edu' and expected_value == 'admin':
                    expected_value = 'director'
                require(getattr(user, '_is_active' if column.name=='is_active' else column.name)==expected_value,
                        'A retained account changed during seeding.')
    require(not db.session.query(Attendance).join(Event).filter(Event.date>now).count(), 'Future attendance is forbidden.')
    return dict(counts)


@click.command('seed-railway-year')
@click.option('--database', required=True, help='Exact new destination database name.')
@click.option('--year', type=click.Choice(['2026']), default='2026', show_default=True)
@click.option('--dry-run', is_flag=True, help='Read-only target/source validation and planned totals.')
@with_appcontext
def seed_railway_year(database, year, dry_run):
    """Provision a new database, copy four logins, and populate the 2026 year."""
    created=[]
    committed=False
    try:
        _target(database)
        tables=set(inspect(db.engine).get_table_names())
        if 'system_settings' in tables:
            marker=db.session.scalar(select(SystemSetting).where(SystemSetting.key==MARKER))
            if marker:
                manifest=json.loads(marker.value)
                require(manifest['version']==VERSION, 'Existing seed version differs; nothing changed.')
                require(manifest['tables']==_fingerprint(), 'Seeded database has changed; nothing was overwritten.')
                require(all(_dest_file(p).is_file() and hashlib.sha256(_dest_file(p).read_bytes()).hexdigest()==h
                            for p,h in manifest['files'].items()), 'Seed documents are missing or changed.')
                click.echo('Existing 2026 seed verified; no changes made.')
                return
        require(not tables, 'Destination is not empty. Use a new database; no reset is performed.')
        now=local_now().replace(second=0, microsecond=0)
        require(datetime(2026,11,1)<=now<datetime(2026,12,21),
                'This 2026 schedule requires 1 November through 20 December 2026; review dates before later use.')
        snapshot=_source_accounts()
        profile_files=_profile_files(snapshot)
        click.echo(f'Target: {db.engine.url.host or "local"} / {database}')
        click.echo('2026: 25 Director goals, 25 commitments, 90 activities, 180 volunteers, 9 coordinators, 90 external participants.')
        click.echo('Retain the four existing default logins; source database is read-only. Mail must remain suppressed.')
        if dry_run:
            click.echo('Dry run complete: no schema, data, or upload files written.')
            return
        phrase=f'SEED 2026 {db.engine.url.host or "local"}/{database}'
        require(click.prompt(f'Type {phrase} to provision the empty destination')==phrase, 'Confirmation did not match; nothing changed.')
        # MySQL DDL commits separately. An interrupted schema is intentionally not reset automatically.
        db.create_all()
        if db.engine.dialect.name in ('mysql','mariadb'):
            require(db.session.execute(text('SELECT @@FOREIGN_KEY_CHECKS')).scalar()==1, 'Foreign keys must be enabled.')
            engines=db.session.execute(text('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=:name'), {'name':database}).scalars().all()
            require(all(engine=='InnoDB' for engine in engines), 'All destination tables must use InnoDB.')
        elif db.engine.dialect.name=='sqlite':
            db.session.execute(text('PRAGMA foreign_keys=ON'))
        with tempfile.TemporaryDirectory(prefix='psu-year-') as staging:
            folder=Path(staging)
            from app import _seed_campuses, _seed_interests_skills, _seed_sdgs
            _seed_campuses(current_app, commit=False)
            _seed_interests_skills(current_app, commit=False)
            _seed_sdgs(current_app, commit=False)
            db.session.flush()
            lookup={c.code:c for c in Campus.query.all()}
            campuses={code:lookup[code] for code in CAMPUS_ORDER}
            accounts=_copy_accounts(snapshot, campuses)
            volunteers, coordinators, external=_people(accounts, campuses, now)
            groups=_activities(folder, campuses, volunteers, coordinators, external, now)
            expected=_goals(campuses, coordinators, accounts, groups, now)
            review_data=_reviews(accounts, now)
            lifecycle=_validate(expected, accounts, snapshot, now)
            for relative, source in profile_files.items():
                staged=folder/relative
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, staged)
            files={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in folder.rglob('*') if p.is_file()}
            for relative in files:
                target=_dest_file(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation protects unrelated uploads, even if names collide.
                with target.open('xb') as stream:
                    created.append(target)
                    stream.write((folder/relative).read_bytes())
            manifest=dict(version=VERSION, year=2026, reference_time_pht=now.isoformat(),
                lifecycle=lifecycle, goals=expected, findings=review_data['findings'], files=files,
                sex_participation=review_data['sex_breakdown'],
                registrations=Registration.query.count(), attendance=Attendance.query.count(),
                sex=dict(Counter(u.sex or 'unrecorded' for u in User.query.filter_by(role='volunteer'))))
            db.session.add(AuditLog(actor_id=accounts['director@psu.edu'].id, action='seed_railway_year',
                target_type='database', details='Generated presentation records; not institutional evidence. '+VERSION,
                created_at=datetime.utcnow()))
            db.session.flush()
            manifest['tables']=_fingerprint()
            db.session.add(SystemSetting(key=MARKER, value=json.dumps(manifest, sort_keys=True)))
            db.session.commit()
            committed=True
        click.echo(f'Created 2026 year: 90 activities, 25 goals, {manifest["registrations"]} registrations, {manifest["attendance"]} attendance records. Four default logins retained.')
    except Exception as exc:
        db.session.rollback()
        if not committed:
            for path in created:
                path.unlink(missing_ok=True)
        if committed:
            raise click.ClickException('Seed committed, but post-commit cleanup failed. Retain the database and uploads; run --dry-run to verify before further action.') from None
        if isinstance(exc, click.ClickException):
            raise
        # Driver errors can include SQL parameters or connection credentials. Never echo them.
        raise click.ClickException('Seed failed; no seed rows committed. Schema may remain after DDL; inspect before recovery. No automatic reset. Error type: '+type(exc).__name__) from None
