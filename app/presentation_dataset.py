"""Guarded replacement of the fictional 2026 presentation dataset."""
import os
import random
from collections import Counter
from datetime import date, datetime, timedelta
from secrets import token_urlsafe

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func, inspect, select, text

from app.campuses import PSU_CAMPUSES, campus_affiliations, validate_catalogue
from app.demo_dataset import DEMO_SERVICE_ID, FIRST_NAMES, LAST_NAMES, RESET_TABLES
from app.models import db
from app.models.annual_plan import (AnnualActivityMapping, AnnualGoalProposal,
                                   AnnualIndicator, AnnualPlan, AnnualResult, AnnualTarget)
from app.models.audit import AuditLog
from app.models.event import (Attendance, CancellationRequest, Campus, Event,
                              EventAnnouncement, Registration, SdgGoal)
from app.models.notification import Notification
from app.models.policy import (ParticipationAgreementRevision, PrivacyAcknowledgement,
                               PrivacyRevision, TermsAcceptance, TermsRevision)
from app.models.user import (Interest, PasswordResetToken, Skill, User, VolunteerProfile,
                             user_interests, user_skills)


KEEP = {'admin@psu.edu': 'director', 'student@psu.edu': 'volunteer',
        'director@psu.edu': 'director', 'coordinator@psu.edu': 'coordinator'}
ANNUAL_TABLES = tuple(model.__table__ for model in (
    AnnualGoalProposal, AnnualActivityMapping, AnnualResult, AnnualTarget,
    AnnualIndicator, AnnualPlan))
CLEAR_TABLES = ANNUAL_TABLES + RESET_TABLES
ACCOUNT_TABLES = (PasswordResetToken.__table__, TermsAcceptance.__table__,
                  PrivacyAcknowledgement.__table__, VolunteerProfile.__table__,
                  user_interests, user_skills)
AGREEMENT = ('Follow the coordinator\'s safety briefing, respect community members, '
             'and keep participant information confidential.')
VERSION = '2026-01'

# Each activity tuple is (title, category, venue, month-day, present, registrations).
# None means upcoming; zero means attendance has not yet been recorded.
CAMPUS_DATA = {
    'LINGAYEN': (12, (3, 32, 12), 14, [
        ('Lingayen Gulf Shoreline Stewardship', 'Environment', 'Lingayen beachfront', '02-21', 13, 17),
        ('Reading Partners at the Community Library', 'Education & Literacy', 'Lingayen community library', '05-16', 13, 16),
        ('Barangay Household Preparedness Workshop', 'Disaster Response', 'Lingayen campus extension hall', '09-19', 13, 19),
        ('Community Records and Digital Skills Clinic', 'Technology & Digital', 'Lingayen campus computer laboratory', '11-14', None, 22),
    ]),
    'URDANETA': (11, (3, 30, 11), 13, [
        ('Computer Basics for Community Learners', 'Technology & Digital', 'Urdaneta campus computer laboratory', '03-14', 11, 13),
        ('Mathematics Learning Support Circle', 'Education & Literacy', 'Urdaneta campus learning resource room', '06-20', 11, 14),
        ('Household First Aid and Safety Orientation', 'Health & Wellness', 'Urdaneta campus multipurpose hall', '10-10', 11, 16),
        ('Career Documents and Online Applications Workshop', 'Technology & Digital', 'Urdaneta campus computer laboratory', '11-21', None, 18),
    ]),
    'BAYAMBANG': (10, (4, 45, 14), 12, [
        ('Family Reading and Storytelling Morning', 'Education & Literacy', 'Bayambang campus reading room', '02-28', 10, 16),
        ('Community Nutrition Learning Session', 'Health & Wellness', 'Bayambang campus extension hall', '04-25', 10, 14),
        ('Learning Materials Preparation Day', 'Education & Literacy', 'Bayambang campus education workshop', '07-18', 10, 15),
        ('Youth Wellness and Recreation Day', 'Sports & Recreation', 'Bayambang campus covered court', '10-17', 10, 17),
    ]),
    'SANCARLOS': (9, (3, 24, 10), 13, [
        ('Community Food Handling and Hygiene Workshop', 'Health & Wellness', 'San Carlos campus training kitchen', '03-21', 13, 17),
        ('Small Enterprise Recordkeeping Clinic', 'Community Development', 'San Carlos campus business laboratory', '08-15', 13, 18),
        ('Community Garden Planting and Care', 'Community Development', 'San Carlos campus demonstration garden', '11-28', None, 20),
    ]),
    'BINMALEY': (9, (3, 25, 10), 12, [
        ('Coastal Waste Segregation Learning Day', 'Environment', 'Binmaley campus fisheries training area', '04-18', 10, 14),
        ('Community Mangrove Care and Monitoring', 'Environment', 'Binmaley coastal learning area', '10-24', 10, 16),
        ('Fishing Household Livelihood Records Clinic', 'Community Development', 'Binmaley campus extension hall', '12-05', None, 19),
    ]),
    'STAMARIA': (8, (3, 24, 9), 9, [
        ('Backyard Vegetable Growing Workshop', 'Community Development', 'Santa Maria campus demonstration farm', '03-07', 8, 9),
        ('Seedling Nursery Care and Distribution', 'Environment', 'Santa Maria campus plant nursery', '06-13', 8, 11),
        ('Composting for Household Gardens', 'Environment', 'Santa Maria campus agricultural learning area', '09-12', 8, 12),
    ]),
    'ASINGAN': (8, (3, 24, 9), 7, [
        ('Community Repair and Maintenance Skills Day', 'Community Development', 'Asingan campus technology workshop', '05-09', 7, 14),
        ('Reading Support for Young Learners', 'Education & Literacy', 'Asingan campus learning resource room', '08-22', 7, 13),
        ('Household Electrical Safety Orientation', 'Disaster Response', 'Asingan campus technology workshop', '12-12', None, 18),
    ]),
    'INFANTA': (6, (2, 16, 7), 8, [
        ('Community Soil and Garden Learning Day', 'Community Development', 'Infanta campus agricultural learning area', '10-03', 0, 11),
        ('Farm Household Enterprise Planning', 'Community Development', 'Infanta campus extension hall', '12-19', None, 18),
    ]),
    'ALAMINOS': (7, (2, 18, 8), 8, [
        ('Community Tourism Information Workshop', 'Arts & Culture', 'Alaminos campus multipurpose hall', '04-11', 8, 13),
        ('Coastal Community Learning Materials Drive', 'Education & Literacy', 'Alaminos campus learning resource room', '09-26', 8, 12),
    ]),
}
EXPECTED_GOALS = {'LINGAYEN': (3, 0), 'URDANETA': (3, 0), 'BAYAMBANG': (1, 0),
                  'SANCARLOS': (2, 0), 'BINMALEY': (0, 3), 'STAMARIA': (3, 0),
                  'ASINGAN': (0, 0), 'INFANTA': (0, 3), 'ALAMINOS': (2, 0)}
CAMPUS_PREFIX = {'LINGAYEN': 'li', 'URDANETA': 'ur', 'BAYAMBANG': 'by',
                 'SANCARLOS': 'sc', 'BINMALEY': 'bn', 'STAMARIA': 'sm',
                 'ASINGAN': 'as', 'INFANTA': 'in', 'ALAMINOS': 'al'}


def _now():
    return datetime.now()


def _require(condition, message):
    if not condition:
        raise click.ClickException(message)


def _preflight(database, now):
    engine = db.engine
    if not current_app.testing:
        _require(os.environ.get('RAILWAY_SERVICE_ID') == DEMO_SERVICE_ID,
                 'Run only in the approved Railway presentation application service.')
        expected_host = os.environ.get('PRESENTATION_DATABASE_HOST')
        _require(expected_host and engine.url.host == expected_host,
                 'PRESENTATION_DATABASE_HOST must match the independently verified presentation database host.')
        _require(engine.dialect.name in ('mysql', 'mariadb'), 'Railway target must be MySQL/MariaDB.')
    _require(database == engine.url.database, 'Database name does not match; no changes made.')
    _require(current_app.config.get('MAIL_SUPPRESS_SEND') is True,
             'Set MAIL_SUPPRESS_SEND=true on the presentation app before continuing.')
    _require(date(2026, 10, 25) <= now.date() < date(2026, 11, 14),
             'This schedule requires 25 October through 13 November 2026. Review activity dates before a later presentation.')
    inspector = inspect(db.session.connection())
    _require(set(inspector.get_table_names()) == set(db.metadata.tables),
             'Schema tables differ from current models; review migrations before resetting.')
    for table in db.metadata.sorted_tables:
        _require({column.name for column in table.columns}.issubset(
            {column['name'] for column in inspector.get_columns(table.name)}),
            f'Schema is missing columns in {table.name}; no changes made.')
    if engine.dialect.name in ('mysql', 'mariadb'):
        _require(db.session.execute(text('SELECT @@FOREIGN_KEY_CHECKS')).scalar() == 1,
                 'Foreign key checks must be enabled.')
        engines = db.session.execute(text(
            'SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = :schema'),
            {'schema': database}).all()
        _require(all(row[1] == 'InnoDB' for row in engines), 'All tables must use transactional InnoDB.')
    elif engine.dialect.name == 'sqlite':
        _require(db.session.execute(text('PRAGMA foreign_keys')).scalar() == 1,
                 'SQLite foreign keys must be enabled for isolated verification.')
    try:
        campuses = validate_catalogue()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None
    _require(len(campuses) == 9 and {(c.name, c.code) for c in campuses} == set(PSU_CAMPUSES),
             'Exactly the nine official campuses are required.')
    accounts = {email: User.query.filter_by(email=email).first() for email in KEEP}
    for email, role in KEEP.items():
        user = accounts[email]
        _require(user is not None and user.role == role and user.is_active,
                 f'Required existing active account {email} must have role {role}.')
    for email in ('student@psu.edu', 'coordinator@psu.edu'):
        _require(accounts[email].campus_id in {c.id for c in campuses},
                 f'{email} must already have an official campus; no account details will be repaired.')
    skills = {row.name for row in Skill.query.all()}
    interests = {row.name for row in Interest.query.all()}
    _require(set(current_app.config['INTEREST_SKILL_MAP']).issubset(interests)
             and {s for names in current_app.config['INTEREST_SKILL_MAP'].values() for s in names}.issubset(skills)
             and {row.number for row in SdgGoal.query.all()} == set(range(1, 18)),
             'Required skill, interest, and SDG catalogues must already be provisioned.')
    return accounts, {c.code: c for c in campuses}


def _clear(accounts):
    keep_ids = [user.id for user in accounts.values()]
    for table in CLEAR_TABLES:
        db.session.execute(table.delete())
    for table in ACCOUNT_TABLES:
        db.session.execute(table.delete().where(table.c.user_id.not_in(keep_ids)))
    for model in (TermsRevision, PrivacyRevision, ParticipationAgreementRevision):
        db.session.execute(model.__table__.update().where(
            model.published_by_id.not_in(keep_ids)).values(published_by_id=None))
    db.session.execute(User.__table__.delete().where(User.id.not_in(keep_ids)))
    VolunteerProfile.query.update({VolunteerProfile.past_participation: []}, synchronize_session=False)
    db.session.expire_all()


def _distinct(users):
    return list({user.id: user for user in users}.values())


def _create_accounts(accounts, campuses):
    rng = random.Random(20261101)
    skills = {row.name: row for row in Skill.query.all()}
    interests = {row.name: row for row in Interest.query.all()}
    volunteers = {}
    coordinator = accounts['coordinator@psu.edu']
    coordinators = {coordinator.campus_id: coordinator}
    index = 0
    for code, (count, _, _, _) in CAMPUS_DATA.items():
        campus = campuses[code]
        volunteers[code] = []
        roles = ['volunteer'] * count + ([] if campus.id in coordinators else ['coordinator'])
        for role in roles:
            name = f'{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[(index * 7) % len(LAST_NAMES)]}'
            identifier = f'23{CAMPUS_PREFIX[code]}{1401 + index:04d}'
            user = User(name=name, email=f'{identifier}@psu.edu.ph', id_number=identifier.upper(),
                        role=role, campus=campus, volunteer_type='student' if role == 'volunteer' else 'staff',
                        sex=rng.choice(('female', 'male', 'prefer_not_to_say')),
                        college_affiliation=rng.choice(campus_affiliations(campus)),
                        created_at=datetime(2026, 1, 12, 9) + timedelta(minutes=index * 19))
            user.set_password(token_urlsafe(32))
            db.session.add(user)
            if role == 'volunteer':
                category = list(current_app.config['INTEREST_SKILL_MAP'])[index % 8]
                user.profile = VolunteerProfile(past_participation=[])
                user.interests = [interests[category]]
                user.skills = [skills[name] for name in current_app.config['INTEREST_SKILL_MAP'][category][:2]]
                volunteers[code].append(user)
            else:
                coordinators[campus.id] = user
            index += 1
    db.session.flush()
    return volunteers, coordinators


def _create_activities(accounts, campuses, volunteers, coordinators, now):
    student = accounts['student@psu.edu']
    everyone = [student] + [user for rows in volunteers.values() for user in rows]
    sdgs = {row.number: row for row in SdgGoal.query.all()}
    skills = {row.name: row for row in Skill.query.all()}
    category_sdgs = {'Environment': (13, 14), 'Education & Literacy': (4, 10),
                     'Technology & Digital': (4, 9), 'Health & Wellness': (3, 10),
                     'Community Development': (2, 11), 'Disaster Response': (11, 13),
                     'Arts & Culture': (4, 11), 'Sports & Recreation': (3, 16)}
    activity_groups, upcoming = {}, []
    for code, (_, _, unique_count, definitions) in CAMPUS_DATA.items():
        campus = campuses[code]
        local = ([student] if student.campus_id == campus.id else []) + volunteers[code]
        visitors = [user for user in everyone if user.campus_id != campus.id]
        pool = _distinct(local + visitors)[:unique_count]
        activity_groups[code] = []
        for index, (title, category, venue, day, present, count) in enumerate(definitions):
            start = datetime.fromisoformat(f'2026-{day}T08:00:00')
            event = Event(title=title, category=category, campus=campus,
                          location=venue, created_by=coordinators[campus.id],
                          description=(f'The {campus.name} extension team will guide volunteers in '
                                       f'{title.lower()}. Tasks include preparing materials, assisting '
                                       'small groups, and documenting follow-up needs. Bring drinking '
                                       'water and arrive 15 minutes before the briefing.'),
                          date=start, end_date=start + timedelta(hours=3 + index % 3),
                          cancellation_deadline=start - timedelta(days=2),
                          slots=count + 4 + index % 3, target_participants=count - 2,
                          participation_agreement_text=AGREEMENT,
                          participation_agreement_version=VERSION)
            event.required_skills_rel = [skills[name] for name in current_app.config['INTEREST_SKILL_MAP'][category]]
            event.sdgs = [sdgs[number] for number in (*category_sdgs[category], 17)]
            db.session.add(event)
            activity_groups[code].append(event)
            if present is None:
                upcoming.append((code, event, count))
                continue
            rotated = pool[index * 3 % len(pool):] + pool[:index * 3 % len(pool)]
            present_users = rotated[:present]
            participants = _distinct(present_users + local + visitors)[:count]
            for seat, user in enumerate(participants):
                recorded = present > 0 and not (code == 'BINMALEY' and index == 1 and seat >= 6)
                status = 'present' if user in present_users else ('excused' if seat % 3 == 0 else 'absent')
                reg = Registration(event=event, user=user,
                                   registered_at=start - timedelta(days=7, minutes=seat * 13),
                                   status='completed' if recorded and status == 'present' else 'confirmed')
                db.session.add(reg)
                if recorded:
                    db.session.add(Attendance(registration=reg, event=event, user=user, status=status))
    db.session.flush()
    registered_ids = {row[0] for row in db.session.query(Registration.user_id).all()}
    uncovered = [user for user in everyone if user.id not in registered_ids]
    default_coordinator = accounts['coordinator@psu.edu']
    older_request = None
    if not any(event.campus_id == default_coordinator.campus_id for _, event, _ in upcoming):
        older_request = Registration.query.join(Event).join(
            Attendance, Attendance.registration_id == Registration.id).filter(
            Event.campus_id == default_coordinator.campus_id, Attendance.status == 'absent').first()
    for index, (code, event, count) in enumerate(upcoming):
        local = volunteers[code]
        participants = _distinct([student] + uncovered + local + everyone)[:count]
        uncovered = [user for user in uncovered if user not in participants]
        for seat, user in enumerate(participants):
            registered = now - timedelta(days=5, minutes=seat * 11)
            reg = Registration(event=event, user=user, registered_at=registered,
                               status='pending' if seat >= 4 and seat % 7 == 0 else 'confirmed')
            db.session.add(reg)
            if seat < 4:
                decision = ('pending', 'approved', 'rejected')[(index * 4 + seat) % 3]
                request_reg = older_request if older_request is not None and index == seat == 0 else reg
                request_event = request_reg.event
                requested = min(now - timedelta(days=2, minutes=seat * 9), request_event.date - timedelta(days=3))
                if decision == 'approved':
                    reg.status = 'cancelled'
                reasons = ('Academic Conflict', 'Transportation Problem', 'Work / Schedule Conflict', 'Family Emergency')
                db.session.add(CancellationRequest(registration=request_reg, reason=reasons[seat],
                    details=('A required class session overlaps the activity.',
                             'Transport arrangements are no longer available.',
                             'My work schedule changed after registration.',
                             'I need to assist a family member.')[seat],
                    status=decision, requested_at=requested,
                    reviewed_at=requested + timedelta(hours=3) if decision != 'pending' else None,
                    reviewed_by=coordinators[request_event.campus_id] if decision != 'pending' else None,
                    review_note=('Request accepted; the place has been released.' if decision == 'approved' else
                                 'Please discuss alternative arrangements with the activity team.' if decision == 'rejected' else None)))
                recipient = coordinators[request_event.campus_id] if decision == 'pending' else user
                db.session.add(Notification(user=recipient, event=request_event,
                    title='Cancellation Request Awaiting Review' if decision == 'pending' else f'Cancellation Request {decision.title()}',
                    message=f'{request_reg.user.name}: {request_event.title}.', notification_type=f'cancellation_{decision}',
                    created_at=requested, is_read=decision != 'pending' and seat % 2 == 0))
            else:
                db.session.add(Notification(user=user, event=event, title='Activity Registration Received',
                    message=f'Your registration for {event.title} has been received.',
                    notification_type='registration', created_at=registered, is_read=seat % 3 == 0))
        if code == 'SANCARLOS':
            db.session.flush()
            event.slots = sum(reg.status == 'confirmed' for reg in event.registrations)
            event.target_participants = min(event.target_participants, event.slots)
        elif code == 'INFANTA':
            event.slots = 0
        if index % 2 == 0:
            db.session.add(EventAnnouncement(event=event, author=coordinators[event.campus_id],
                announcement_type='event_update', message='Please bring drinking water and a reusable notebook. The team will provide activity materials.',
                created_at=now - timedelta(days=1)))
    db.session.flush()
    return activity_groups


def _create_goals(campuses, activity_groups):
    plans = {}
    for kind in ('AOP', 'ASP'):
        plan = AnnualPlan(source_key=f'presentation:2026:{kind}', year=2026, plan_type=kind,
                          title=f'2026 Community Extension {kind}', status='approved',
                          source_document='2026 Community Extension Work Programme',
                          approval_date=date(2026, 1, 20))
        db.session.add(plan)
        plans[kind] = plan
    definitions = [('activities', 'Community outreach activities delivered', 'activities', 'AOP'),
                   ('verified_attendance', 'Verified volunteer participation', 'attendance occurrences', 'AOP'),
                   ('unique_attendees', 'Individual volunteers engaged', 'people', 'ASP')]
    for code in [*CAMPUS_DATA, 'UNIVERSITY']:
        campus = campuses.get(code)
        values = CAMPUS_DATA[code][1] if campus else (20, 220, 60)
        events = activity_groups[code] if campus else [event for rows in activity_groups.values() for event in rows]
        for index, (basis, name, unit, kind) in enumerate(definitions):
            key = f'presentation:2026:{code}:{basis}'
            indicator = AnnualIndicator(source_key=key, plan=plans[kind], code=f'{code}-{index + 1}',
                name=name, program='Community Extension', definition=f'Count {name.lower()} from linked activity records.',
                unit=unit, responsible_office=f'{campus.name} Extension Office' if campus else 'University Extension Office',
                evidence_basis=basis)
            target = AnnualTarget(source_key=key, indicator=indicator, campus=campus,
                                  target_value=values[index], comparison_rule='gte', deadline=date(2026, 12, 31))
            db.session.add(target)
            db.session.add_all([AnnualActivityMapping(target=target, event=event) for event in events])
    db.session.flush()


def _validate_dataset(accounts, campuses, before, now):
    from app.annual_goals import summary
    from app.reports import build_events_report
    _require(User.query.count() == 92 and Event.query.count() == 28, 'Account/activity count validation failed.')
    _require(User.query.filter_by(role='volunteer').count() == 81
             and User.query.filter_by(role='coordinator').count() == 9, 'Role counts failed.')
    after = {email: {column.name: getattr(user, column.key) for column in User.__table__.columns
                     if column.name != 'is_active'} | {'is_active': user.is_active}
             for email, user in accounts.items()}
    _require(before == after, 'A preserved account changed; replacement aborted.')
    _require(Counter(row.status for row in CancellationRequest.query.all()) ==
             {'pending': 8, 'approved': 8, 'rejected': 8}, 'Cancellation counts failed.')
    _require(AnnualTarget.query.count() == 30 and AnnualResult.query.count() == 0, 'Goal counts failed.')
    _require(Registration.query.filter_by(user_id=accounts['student@psu.edu'].id).count() > 3,
             'Default student participation is missing.')
    for user in User.query.filter_by(role='volunteer').all():
        _require(Registration.query.filter_by(user_id=user.id).count() > 0, 'A volunteer has no application.')
    for record in Attendance.query.all():
        reg = record.registration
        _require(reg.user_id == record.user_id and reg.event_id == record.event_id
                 and reg.event.end_date < now and reg.status == ('completed' if record.status == 'present' else 'confirmed'),
                 'Attendance consistency failed.')
    for request in CancellationRequest.query.all():
        reg = request.registration
        _require(reg.registered_at < request.requested_at < reg.event.cancellation_deadline
                 and reg.status == ('cancelled' if request.status == 'approved' else 'confirmed'),
                 f'Cancellation consistency failed for registration {reg.id} ({reg.status}, {request.status}).')
    for code, expected in EXPECTED_GOALS.items():
        actual = summary(2026, campuses[code].id)
        _require((actual['met'], actual['pending']) == expected, f'{code} goal outcomes failed.')
    _require(summary(2026)['pending'] == 3, 'University incomplete evidence must remain pending.')
    campus_id = accounts['coordinator@psu.edu'].campus_id
    _require(CancellationRequest.query.join(Registration).join(Event).filter(
        Event.campus_id == campus_id, CancellationRequest.status == 'pending').count() > 0,
        'Default coordinator has no pending cancellation review.')
    incomplete, _ = build_events_report(campus_id=campus_id, attention='pending_attendance', now=now)
    low, _ = build_events_report(campus_id=campus_id, attention='low_attendance', now=now)
    _require(incomplete or low, 'Default coordinator has no attendance follow-up.')


@click.command('reset-and-seed-presentation')
@click.option('--database', required=True, help='Exact configured presentation database name.')
@click.option('--dry-run', is_flag=True, help='Inspect destination and counts without writing.')
@with_appcontext
def reset_and_seed_presentation(database, dry_run):
    """Replace presentation records while retaining the four default accounts."""
    try:
        now = _now()
        accounts, campuses = _preflight(database, now)
        before = {email: {column.name: getattr(user, column.key) for column in User.__table__.columns
                          if column.name != 'is_active'} | {'is_active': user.is_active}
                  for email, user in accounts.items()}
        target = f'{db.engine.url.host or "local"}/{database}'
        click.echo(f'Target: {target}; service: {os.environ.get("RAILWAY_SERVICE_ID", "isolated testing")}')
        click.echo('Preserve: ' + ', '.join(f'{email} (ID {user.id}, {user.role})' for email, user in accounts.items()))
        for table in CLEAR_TABLES:
            count = db.session.scalar(select(func.count()).select_from(table))
            click.echo(f'Clear {table.name}: {count}')
        keep_ids = [user.id for user in accounts.values()]
        click.echo(f'Remove other accounts: {User.query.filter(User.id.not_in(keep_ids)).count()}')
        for table in ACCOUNT_TABLES:
            count = db.session.scalar(select(func.count()).select_from(table).where(table.c.user_id.not_in(keep_ids)))
            click.echo(f'Clear other-account {table.name}: {count}')
        click.echo('Create: 80 volunteers + 8 coordinators; 92 total accounts; 28 activities (22 ended, 6 upcoming); '
                   '30 goals; 24 cancellation requests (8 pending, 8 approved, 8 rejected).')
        click.echo('Preserve catalogues, settings, policy revisions and default-account acceptances. Uploaded files stay untouched.')
        if dry_run:
            return
        phrase = f'RESET PRESENTATION {target}'
        _require(click.prompt(f'After backing up and pausing writes, type {phrase}') == phrase,
                 'Confirmation did not match; no changes made.')
        _clear(accounts)
        volunteers, coordinators = _create_accounts(accounts, campuses)
        activities = _create_activities(accounts, campuses, volunteers, coordinators, now)
        _create_goals(campuses, activities)
        db.session.add(AuditLog(actor=accounts['admin@psu.edu'], action='presentation_dataset_reset',
            target_type='database', details='Fictional presentation records; not institutional evidence. '
            '2026 dataset: 28 activities, 80 new volunteers, 8 new coordinators; four default accounts retained.', created_at=now))
        db.session.flush()
        _validate_dataset(accounts, campuses, before, now)
        registrations = Registration.query.count()
        attendance = Attendance.query.count()
        db.session.commit()
        click.echo(f'Created 28 activities, {registrations} registrations, {attendance} attendance records, '
                   '30 goals and 24 cancellation requests. Four default accounts preserved; 92 total accounts.')
    finally:
        db.session.rollback()
