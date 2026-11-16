"""An isolated, reproducible calendar year for local report demonstrations."""
import io
import json
import random
import secrets
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import before_render_template, current_app, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import event as sa_event, inspect

from app.models import db
from app.models.annual_plan import (AnnualActivityMapping, AnnualIndicator, AnnualPlan,
                                   AnnualResult, AnnualTarget)
from app.models.event import (Attendance, Campus, Event, ExternalParticipant,
                              HistoricalActivity, Milestone, Registration, SdgGoal)
from app.models.user import Interest, Skill, SystemSetting, User, VolunteerProfile
from app.models.workspace import ExternalGroup, PartnerAgency, PartnerAgreement

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / '.qa-report-year-temp'
MARKER = 'report-year-demo-v1'
NOTICE = 'Synthetic Demonstration Data'
LOGIN_EMAILS = {'director':'director@psu.edu', 'coordinator':'coordinator@psu.edu',
                'volunteer':'student@psu.edu'}


def demo_path(database):
    path = Path(database).resolve()
    if not path.is_relative_to(DEMO_ROOT.resolve()) or path.suffix != '.sqlite':
        raise ValueError('Use a .sqlite database inside .qa-report-year-temp only.')
    return path


def validate_target(database, year):
    database = demo_path(database)
    if not 2000 <= year < date.today().year:
        raise ValueError('Choose a completed calendar year from 2000 onward.')
    if database.exists():
        import sqlite3
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
            try:
                marker = connection.execute('SELECT value FROM system_settings WHERE key=?',
                                            (MARKER,)).fetchone()
            except sqlite3.DatabaseError as exc:
                raise ValueError('The existing database is not a report demonstration database.') from exc
            if marker != (str(year),):
                raise ValueError('Existing database has no matching demo/year marker; nothing changed.')
    return database


def create_demo_app(database, year=2025):
    """Explicit configuration never reads or copies the operational database."""
    from app import create_app
    from config import DevelopmentConfig, config
    database = validate_target(database, year)
    database.parent.mkdir(parents=True, exist_ok=True)
    private = database.parent / (database.stem + '-private')
    config['report_demo'] = type('ReportDemoConfig', (DevelopmentConfig,), dict(
        SQLALCHEMY_DATABASE_URI='sqlite:///' + database.as_posix(),
        SQLALCHEMY_ENGINE_OPTIONS={}, REPORT_DEMO_MODE=True, REPORT_DEMO_YEAR=year,
        SECRET_KEY=secrets.token_hex(32), DEBUG=False, MAIL_SUPPRESS_SEND=True,
        PRIVATE_UPLOAD_FOLDER=str(private), UPLOAD_FOLDER=str(private / 'evidence'),
        SESSION_COOKIE_NAME='psu_report_demo', SESSION_COOKIE_SECURE=False,
    ))
    app = create_app('report_demo')
    with app.app_context():
        @sa_event.listens_for(db.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    install_demo_views(app)
    return app


def seed_year(year, password):
    """One transaction, no deletion; repeat runs validate and return the manifest."""
    if not current_app.config.get('REPORT_DEMO_MODE') or db.engine.dialect.name != 'sqlite':
        raise ValueError('The report seeder requires the dedicated local demo application.')
    path = demo_path(db.engine.url.database)
    if current_app.config['REPORT_DEMO_YEAR'] != year:
        raise ValueError('Configured demo year does not match.')
    if inspect(db.engine).has_table('system_settings'):
        existing = db.session.scalar(db.select(SystemSetting).filter_by(key=MARKER))
        if existing:
            if existing.value != str(year):
                raise ValueError('Demo belongs to another year.')
            return manifest(year)
    if inspect(db.engine).has_table('users') and db.session.scalar(db.select(db.func.count()).select_from(User)):
        raise ValueError('Refusing to seed a database containing existing accounts.')
    db.create_all()
    try:
        _populate(year, password)
        db.session.add(SystemSetting(key=MARKER, value=str(year)))
        db.session.flush()
        result = manifest(year)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    (path.parent / (path.stem + '-manifest.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def sample_pdf(filename, title, lines):
    from reportlab.pdfgen import canvas
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'proposals'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    stream = io.BytesIO()
    page = canvas.Canvas(stream)
    page.setTitle(f'{NOTICE}: {title}')
    page.setFont('Helvetica-Bold', 14)
    page.drawString(45, 790, NOTICE)
    page.setFont('Helvetica', 11)
    for index, line in enumerate([title, 'Fictional records for local testing; no institutional approval.', *lines]):
        page.drawString(45, 760 - index * 22, str(line)[:95])
    page.save()
    path.write_bytes(stream.getvalue())
    return {'path': filename, 'name': filename, 'readable': True}


def _populate(year, password):
    from app import _seed_interests_skills, _seed_sdgs
    from app.campuses import campus_affiliations, seed_catalogue
    from app.demo_dataset import ACTIVITIES, FIRST_NAMES, LAST_NAMES
    seed_catalogue(commit=False)
    _seed_interests_skills(current_app, commit=False)
    _seed_sdgs(current_app, commit=False)
    campuses = Campus.query.order_by(Campus.id).all()
    skills = {s.name: s for s in Skill.query.all()}
    interests = {i.name: i for i in Interest.query.all()}
    sdgs = {s.number: s for s in SdgGoal.query.all()}
    rng = random.Random(year)
    joined = datetime(year - 1, 10, 1)
    disabled_hash = User(name='unused', email='unused@demo.invalid')
    disabled_hash.set_password(secrets.token_urlsafe(40))
    login_hash = User(name='unused', email='unused@demo.invalid')
    login_hash.set_password(password)

    def account(index, role, campus, email=None):
        name = f'{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[index // len(FIRST_NAMES) % len(LAST_NAMES)]}'
        user = User(name=name, email=email or f'{role}-{index:04d}@demo.invalid',
                    id_number=f'DEMO-{role[:3].upper()}-{index:04d}', role=role, campus=campus,
                    volunteer_type=('student', 'faculty', 'staff')[index % 3],
                    sex=('female', 'male', 'female', 'male', 'prefer_not_to_say')[index % 5],
                    college_affiliation=campus_affiliations(campus)[index % len(campus_affiliations(campus))],
                    password_hash=login_hash.password_hash if email else disabled_hash.password_hash,
                    first_use_guide_dismissed_at=joined, created_at=joined + timedelta(days=index % 70))
        if role == 'volunteer':
            user.profile = VolunteerProfile()
            category = ACTIVITIES[index % len(ACTIVITIES)][1]
            user.interests = [interests[category]]
            user.skills = [skills[n] for n in current_app.config['INTEREST_SKILL_MAP'][category]]
        db.session.add(user)
        return user

    director = account(900, 'director', campuses[0], LOGIN_EMAILS['director'])
    coordinators = [account(1000 + i, 'coordinator', c,
                           LOGIN_EMAILS['coordinator'] if i == 0 else None) for i, c in enumerate(campuses)]
    volunteers = [account(i, 'volunteer', campuses[i % 9],
                          LOGIN_EMAILS['volunteer'] if i == 0 else None) for i in range(450)]
    external = []
    for i in range(180):
        person = ExternalParticipant(id_number=f'DEMO-EXT-{i:04d}',
            name=f'{FIRST_NAMES[i % 25]} {LAST_NAMES[(i + 17) % len(LAST_NAMES)]}',
            email=f'community-{i}@demo.invalid', sex=('male', 'female', None)[i % 3], created_at=joined)
        db.session.add(person)
        external.append(person)
    db.session.flush()
    activities = []
    campus_counts = [32, 29, 25, 24, 23, 22, 22, 20, 19]
    for ci, campus in enumerate(campuses):
        months = sorted([*range(1, 13), *rng.choices(range(1, 13),
            weights=[1, 2, 3, 2, 1, 1, 1, 2, 3, 3, 3, 1], k=campus_counts[ci] - 12)])
        agency = PartnerAgency(campus_id=campus.id, name=f'{campus.name} Community Learning Circle (Fictional)',
                               contact_name=f'{campus.name} Demo Liaison', email=f'partner-{ci}@demo.invalid')
        db.session.add(agency)
        db.session.flush()
        document = sample_pdf(f'demo-{year}-moa-{ci}.pdf', f'{campus.name} Sample Agreement',
                              [f'Validity: 01 January - 31 December {year}', 'Community outreach and learning support.'])
        agreement = PartnerAgreement(agency_id=agency.id, reference=f'DEMO-MOA-{year}-{ci+1:02d}',
                                    valid_from=date(year, 1, 1), valid_until=date(year, 12, 31), document=document)
        db.session.add(agreement)
        db.session.flush()
        for j, month in enumerate(months):
            title, category, goals = ACTIVITIES[(j + ci * 2) % len(ACTIVITIES)]
            start = datetime(year, month, 4 + (j * 5 + ci * 3) % 23, 8 + j % 3)
            cancelled = (j + ci * 3) % 17 == 0
            event = Event(title=f'{title} — {campus.name}',
                description=f'{NOTICE}. {campus.name} volunteers support community learning and practical outreach through {title.lower()}. Activities include a briefing, guided small-group work, and a closing review.',
                campus=campus, created_by=coordinators[ci], date=start, end_date=start + timedelta(hours=3 + j % 4),
                cancellation_deadline=start - timedelta(days=1), location=f'{campus.name} community learning area',
                category=category, conducting_department=campus_affiliations(campus)[j % len(campus_affiliations(campus))],
                participant_type='Students, faculty, staff, and community participants',
                audience={'departments': [campus_affiliations(campus)[j % len(campus_affiliations(campus))]]},
                slots=55 + (ci * 7 + j) % 35, target_participants=22 + (ci * 3 + j) % 22,
                lifecycle_status='cancelled' if cancelled else 'approved',
                cancellation_reason='Community venue unavailable; activity retained for the demonstration record.' if cancelled else None,
                cancelled_at=start - timedelta(days=3) if cancelled else None,
                agreement_id=agreement.id, participation_agreement_text='Synthetic agreement: follow the safety briefing and respect community privacy.',
                participation_agreement_version=f'demo-{year}')
            event.required_skills_rel = [skills[n] for n in current_app.config['INTEREST_SKILL_MAP'][category]]
            event.sdgs = [sdgs[n] for n in sorted(set((*goals, 17))) ]
            if j % 6 == 0:
                event.proposal_document = sample_pdf(f'demo-{year}-proposal-{ci}-{j}.pdf', event.title,
                    [f'Start: {start}', f'End: {event.end_date}', f'Campus: {campus.name}', 'Sample coordinator-reviewed proposal.'])
            db.session.add(event)
            db.session.flush()
            activities.append(event)
            group = ExternalGroup(event_id=event.id, name=f'{campus.name} Community Learning Group')
            db.session.add(group)
            db.session.flush()
            count = 26 + rng.randrange(23) + ci % 3
            campus_volunteers = volunteers[ci::9]
            selected = rng.sample(campus_volunteers, count - 5)
            people = [(u, None) for u in selected] + [(None, e) for e in rng.sample(external[ci*20:(ci+1)*20], 5)]
            incomplete = j in (10, 22) and ci % 3 != 0
            for seat, (user, person) in enumerate(people):
                withdrawn = cancelled or seat % 19 == 0
                status = None if withdrawn or (incomplete and seat % 4 == 0) else rng.choices(
                    ['present', 'absent', 'excused'], weights=[79 + ci, 16 - ci, 5])[0]
                reg = Registration(event=event, user=user, external_participant=person,
                    status='cancelled' if withdrawn else 'completed' if status == 'present' else 'confirmed',
                    registered_at=start - timedelta(days=5 + seat % 18), policy_accepted_at=start - timedelta(days=5 + seat % 18),
                    policy_version='synthetic-demo')
                if person:
                    if person.group_id is None:
                        person.group_id = group.id
                    reg.external_privacy_accepted_at = reg.registered_at
                    reg.external_privacy_version = 'synthetic-demo'
                db.session.add(reg)
                if status:
                    db.session.add(Attendance(registration=reg, event=event, user_id=user.id if user else None, status=status))
            if event.proposal_document:
                db.session.add(Milestone(event=event, filename=f'demo-{year}-evidence-{ci}-{j}.pdf',
                    upload_path='proposals/' + event.proposal_document['path'],
                    category='report', uploaded_by_id=coordinators[ci].id, uploaded_at=start + timedelta(hours=2)))
        for k in range(3):
            db.session.add(HistoricalActivity(source_key=f'demo-historical-{year}-{ci}-{k}',
                source_document=f'{NOTICE}: separate illustrative historical register', source_page=ci + 1,
                source_row=k+1, unit_name=campus.name, campus_id=campus.id,
                title=f'Synthetic Historical Record: {("Community Literacy", "Coastal Stewardship", "Wellness Outreach")[k]}',
                activity_type=('Extension', 'Outreach', 'Training')[k], partners=agency.name,
                participant_categories='Community participants', volunteer_count=30 + ci*3 + k*7,
                year_conducted=year, imported_by_id=director.id))
    db.session.flush()
    _annual_plans(year, campuses, activities)


def _annual_plans(year, campuses, activities):
    end = date(year, 12, 31)
    plans = {}
    for kind in ('AOP', 'ASP'):
        plan = AnnualPlan(source_key=f'demo-{year}-{kind}', year=year, plan_type=kind,
            title=f'{NOTICE}: {year} {kind}', source_document=f'Synthetic {kind} planning register',
            approval_reference=f'DEMO-{kind}-{year}', approval_date=date(year, 1, 2))
        db.session.add(plan)
        db.session.flush()
        plans[kind] = plan
    for ci, campus in enumerate([*campuses, None]):
        events = [e for e in activities if e.lifecycle_status == 'approved' and (campus is None or e.campus_id == campus.id)]
        if campus is None:
            supported = {campuses[i].id for i in (0, 3, 6)}
            events = [e for e in events if e.campus_id in supported]
        for kind in ('AOP', 'ASP'):
            for index, (basis, unit) in enumerate((('activities', 'activities'), ('verified_attendance', 'attendance occurrences'), ('approved_aggregate', 'partnerships'))):
                key = f'demo-{year}-{ci}-{kind}-{index}'
                names = ['Community Activities Delivered', 'Verified Community Participation', 'Supported Community Partnerships']
                indicator = AnnualIndicator(source_key=key, plan_id=plans[kind].id,
                    code=f'DEMO-{ci+1:02d}-{index+1}', program='Community Extension and Volunteer Development',
                    name=('University-Supported ' if campus is None else '') + names[index], definition=f'{NOTICE}. ' + ('Count fully recorded ended activities.' if index == 0 else 'Count recorded presence, including repeat attendance.' if index == 1 else 'Separate fictional approved aggregate; not derived from activity counts.') + (' University-supported activity cohort: Lingayen, Bayambang, and San Carlos.' if campus is None and index < 2 else ''),
                    unit=unit, responsible_office='Campus Extension Office' if campus else 'University Extension Office',
                    evidence_basis=basis, shared_key=f'demo-shared-{year}-{ci}-{index}' if index < 2 else None)
                db.session.add(indicator)
                db.session.flush()
                target = AnnualTarget(source_key=key, indicator=indicator, campus=campus,
                    target_value=(18 + ci % 3 if campus else 70) if index == 0 else (400 + ci*45 if campus else 2500) if index == 1 else 4 + ci % 4,
                    deadline=end, activity_scope='Synthetic activity records' if campus else 'University-supported cohort: Lingayen, Bayambang, San Carlos')
                db.session.add(target)
                db.session.flush()
                if index < 2:
                    for event in events:
                        db.session.add(AnnualActivityMapping(target=target, event=event))
                else:
                    pending = campus is not None and ci % 4 == 0
                    db.session.add(AnnualResult(source_key=key, target=target,
                        actual_value=None if pending else 6 if campus is None else (2 + (ci + (kind == 'ASP')) % 7),
                        evidence_status='pending' if pending else 'verified', result_type='approved_aggregate',
                        source_document='Synthetic partnership evidence register',
                        coverage_note='Fictional aggregate for local report demonstrations only.',
                        coverage_start=date(year, 1, 1), coverage_end=end))


def manifest(year):
    from app.services.workspace_reports import workspace_report
    from app.annual_goals import comparisons, summary
    from werkzeug.datastructures import MultiDict
    director = User.query.filter_by(email=LOGIN_EMAILS['director']).one()
    data = workspace_report(Event.query, MultiDict({'year':str(year), 'period':'annual'}), director, datetime.now())
    return dict(year=year, synthetic=True, activities=Event.query.count(),
        volunteers=User.query.filter_by(role='volunteer').count(), external_people=ExternalParticipant.query.count(),
        registrations=Registration.query.count(), recorded_attendance=Attendance.query.count(),
        attendance_states=dict(Counter(a.status for a in Attendance.query.all())),
        registration_states=dict(Counter(r.status for r in Registration.query.all())),
        lifecycle=dict(Counter(e.lifecycle_status for e in Event.query.all())),
        monthly=dict(zip(data['month_labels'], data['monthly'])),
        campuses=data['campus_chart'],
        annual_campuses=[dict(campus=c['campus'], total=c['total'], achieved=c['met'], pending=c['pending']) for c in comparisons(year)],
        university_targets={k:summary(year)[k] for k in ('total', 'met', 'pending')},
        historical_records=HistoricalActivity.query.count(),
        report_totals={key:data[key] for key in ('approved', 'conducted', 'attendees', 'accounts')})


def install_demo_views(app):
    @before_render_template.connect_via(app)
    def no_prior_year_comparison(sender, template, context, **extra):
        previous = context.get('previous')
        if previous and previous[0].year != app.config['REPORT_DEMO_YEAR']:
            context['deltas'] = {}

    @app.before_request
    def default_demo_year():
        if request.method == 'GET' and current_user.is_authenticated and request.endpoint == 'workspace.recognition' and 'award_year' not in request.args:
            return redirect(url_for('workspace.recognition', award_year=app.config['REPORT_DEMO_YEAR']))
        if request.method == 'GET' and current_user.is_authenticated and request.endpoint in (
            'workspace.overview', 'workspace.report_results', 'workspace.aop',
            'workspace.historical', 'workspace.people_insights', 'goals.details') and 'year' not in request.args:
            args = request.args.to_dict(flat=False)
            args['year'] = [str(app.config['REPORT_DEMO_YEAR'])]
            return redirect(url_for(request.endpoint, **(request.view_args or {}), **args))

    @app.get('/demo')
    def report_demo_directory():
        return render_template('workspace/report_demo.html', demo_year=app.config['REPORT_DEMO_YEAR'])

    @app.after_request
    def mark_demo_download(response):
        disposition = response.headers.get('Content-Disposition', '')
        if response.status_code != 200 or 'attachment' not in disposition:
            return response
        response.headers['X-Report-Data'] = 'synthetic-demonstration-only'
        # Documents already carry a notice; report downloads get one inside too.
        report_endpoint = request.endpoint in ('workspace.export', 'workspace.historical_export', 'goals.details') or (
            request.endpoint or '').startswith(('director.export_', 'coordinator.export_'))
        if not report_endpoint:
            return response
        response.direct_passthrough = False
        label = f'{NOTICE} — {app.config["REPORT_DEMO_YEAR"]}; not an official PSU report.'
        from werkzeug.http import parse_options_header, dump_options_header
        kind, options = parse_options_header(disposition)
        fmt = Path(options.get('filename', '')).suffix.lstrip('.')
        raw = response.get_data()
        if fmt == 'csv':
            response.set_data((label + '\r\n').encode('utf-8-sig') + raw.removeprefix(b'\xef\xbb\xbf'))
        elif fmt == 'xlsx':
            from openpyxl import load_workbook
            book = load_workbook(io.BytesIO(raw))
            sheet = book.create_sheet('Demo Notice', 0)
            sheet.append([label]); sheet.column_dimensions['A'].width = 100
            output = io.BytesIO(); book.save(output); response.set_data(output.getvalue())
        elif fmt == 'pdf':
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            reader = PdfReader(io.BytesIO(raw)); writer = PdfWriter()
            for page in reader.pages:
                overlay = io.BytesIO(); c = canvas.Canvas(overlay, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
                c.setFont('Helvetica-Bold', 9); c.drawString(24, 15, label); c.save()
                page.merge_page(PdfReader(overlay).pages[0]); writer.add_page(page)
            output = io.BytesIO(); writer.write(output); response.set_data(output.getvalue())
        options['filename'] = 'synthetic-' + options.get('filename', 'report.' + (fmt or 'bin'))
        response.headers['Content-Disposition'] = dump_options_header(kind, options)
        return response
