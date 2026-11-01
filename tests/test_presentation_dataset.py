"""Presentation reset checks run only against isolated databases with foreign keys enabled."""
from collections import Counter
from datetime import datetime
import os
import re

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url

from app import create_app
from app.annual_goals import campus_ranking, comparisons, summary
from app.models import db
from app.models.annual_plan import (AnnualActivityMapping, AnnualGoalProposal, AnnualIndicator,
                                   AnnualPlan, AnnualResult, AnnualTarget)
from app.models.audit import AuditLog
from app.models.event import (Attendance, CancellationRequest, Campus, Event, ExternalParticipant,
                              EventAnnouncement, HistoricalActivity, Milestone, AnalyticsSummary,
                              RecommendationLog, Registration)
from app.models.notification import Notification
from app.models.policy import (TermsRevision, TermsAcceptance, PrivacyRevision,
                               PrivacyAcknowledgement, ParticipationAgreementRevision)
from app.models.user import (PasswordResetToken, SystemSetting, User, VolunteerProfile)
from app.presentation_dataset import CAMPUS_DATA, EXPECTED_GOALS, KEEP, DEMO_SERVICE_ID
from app.reports import build_events_report


NOW = datetime(2026, 11, 1, 12)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr('app.presentation_dataset._now', lambda: NOW)
    instance = create_app('testing')
    with instance.app_context():
        db.session.remove()
        with db.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
        student = User.query.filter_by(email='student@psu.edu').one()
        student.sex = 'female'
        db.session.commit()
    # Keep real hashes on the four existing accounts; only speed up generated identities.
    monkeypatch.setattr(User, 'set_password', lambda self, password: setattr(self, 'password_hash', 'unusable-generated-hash'))
    yield instance
    with instance.app_context():
        db.session.remove()
        db.engine.dispose()


def invoke(app, answer='RESET PRESENTATION local/:memory:\n', *options):
    return app.test_cli_runner().invoke(
        args=['reset-and-seed-presentation', '--database', ':memory:', *options], input=answer)


def snapshot():
    return {table.name: [tuple(row) for row in db.session.execute(select(table)).all()]
            for table in db.metadata.sorted_tables}


def test_dry_run_and_confirmation_never_write(app):
    with app.app_context():
        before = snapshot()
    result = invoke(app, None, '--dry-run')
    assert result.exit_code == 0, (result.output, result.exception)
    assert 'admin@psu.edu' in result.output and '92 total accounts' in result.output
    assert 'Clear annual_activity_mappings:' in result.output
    assert 'Remove other accounts: 2' in result.output
    assert invoke(app, 'RESET ALL DEMO local/:memory:\n').exit_code != 0
    with app.app_context():
        assert snapshot() == before


def test_target_and_mail_guards(app, monkeypatch):
    app.testing = False
    monkeypatch.setenv('RAILWAY_SERVICE_ID', 'main-service')
    assert 'approved Railway presentation' in invoke(app).output
    monkeypatch.setenv('RAILWAY_SERVICE_ID', DEMO_SERVICE_ID)
    monkeypatch.setenv('PRESENTATION_DATABASE_HOST', 'wrong-host')
    assert 'independently verified' in invoke(app).output
    app.testing = True
    result = app.test_cli_runner().invoke(args=['reset-and-seed-presentation', '--database', 'wrong'])
    assert result.exit_code != 0 and 'does not match' in result.output
    app.config['MAIL_SUPPRESS_SEND'] = False
    assert 'MAIL_SUPPRESS_SEND=true' in invoke(app).output
    with app.app_context():
        assert User.query.count() == 6


@pytest.mark.parametrize('problem', ['account', 'role', 'inactive', 'campus', 'catalogue', 'schema', 'foreign_keys', 'date'])
def test_invalid_preconditions_leave_records_untouched(app, monkeypatch, problem):
    with app.app_context():
        user = User.query.filter_by(email='admin@psu.edu').one()
        if problem == 'account':
            user.email = 'renamed@example.org'
        elif problem == 'role':
            user.role = 'director'
        elif problem == 'inactive':
            user._is_active = False
        elif problem == 'campus':
            User.query.filter_by(email='coordinator@psu.edu').one().campus_id = None
        elif problem == 'catalogue':
            Campus.query.filter_by(code='LINGAYEN').one().name = 'Other campus'
        elif problem == 'schema':
            db.session.execute(text('ALTER TABLE annual_results RENAME COLUMN coverage_note TO missing_note'))
        elif problem == 'foreign_keys':
            db.session.remove()
            with db.engine.connect() as connection:
                connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
        elif problem == 'date':
            monkeypatch.setattr('app.presentation_dataset._now', lambda: datetime(2026, 11, 14))
        db.session.commit()
        before = snapshot() if problem != 'schema' else Event.query.count()
    result = invoke(app)
    assert result.exit_code != 0, result.output
    with app.app_context():
        assert (snapshot() if problem != 'schema' else Event.query.count()) == before


def test_complete_dataset_and_expected_reporting(app):
    with app.app_context():
        preserved = {user.email: (user.id, user.password_hash, user.name, user.campus_id, user.auth_version)
                     for user in User.query.filter(User.email.in_(KEEP)).all()}
    for _ in range(2):
        result = invoke(app)
        assert result.exit_code == 0, (result.output, result.exception)
        with app.app_context():
            assert User.query.count() == 92
            assert Event.query.count() == 28
            assert ExternalParticipant.query.count() == 0
            assert Counter(request.status for request in CancellationRequest.query.all()) == {'pending': 8, 'approved': 8, 'rejected': 8}
            assert AnnualTarget.query.count() == 30
            assert AnnualPlan.query.count() == 2
            assert AnnualResult.query.count() == 0
            assert AuditLog.query.one().action == 'presentation_dataset_reset'
            assert {user.email: (user.id, user.password_hash, user.name, user.campus_id, user.auth_version)
                    for user in User.query.filter(User.email.in_(KEEP)).all()} == preserved
            generated = User.query.filter(User.email.not_in(KEEP)).all()
            assert len({user.name for user in generated}) == 88
            assert all(user.email.endswith('@psu.edu.ph') and user.id_number for user in generated)
            authored = [value for user in generated for value in (user.name, user.email, user.id_number)]
            authored += [value for event in Event.query.all() for value in (
                event.title, event.description, event.location, event.participation_agreement_text)]
            authored += [note.title + ' ' + note.message for note in Notification.query.all()]
            assert not any(re.search(r'\b(demo|test|sample|synthetic)\b', value, re.I) for value in authored)
            assert not any('23ur0679' in user.email for user in generated)
            assert {user.sex for user in generated} == {'female', 'male', 'prefer_not_to_say'}
            for user in generated:
                from app.campuses import campus_affiliations
                assert user.college_affiliation in campus_affiliations(user.campus)
                if user.role == 'volunteer':
                    assert user.registrations and user.profile and user.skills and user.interests
            for code, (count, _, _, events) in CAMPUS_DATA.items():
                campus = Campus.query.filter_by(code=code).one()
                assert User.query.filter(User.email.not_in(KEEP), User.role == 'volunteer', User.campus_id == campus.id).count() == count
                assert User.query.filter_by(role='coordinator', campus_id=campus.id).count() == 1
                assert Event.query.filter_by(campus_id=campus.id).count() == len(events)
                plan = summary(2026, campus.id)
                assert (plan['met'], plan['pending']) == EXPECTED_GOALS[code]
            ranking = campus_ranking(comparisons(2026), lowest=True)
            assert any(row['campus'] == 'Asingan' for row in ranking['leaders'])
            assert summary(2026)['pending'] == 3
            rows, totals = build_events_report(start_date='2026-01-01', end_date='2026-12-31', now=NOW)
            assert totals['event_count'] == 28
            assert sum(row['ended'] for row in rows) == 22
            assert sum(row['ended'] and not row['attendance_complete'] for row in rows) == 2
            assert any(row['attendance_complete'] and row['outcome_attended'] < row['registrations'] * .75 for row in rows)
            assert any(row['attendance_complete'] and row['outcome_attended'] < row['target_participants'] for row in rows)
            future = Event.query.filter(Event.date > NOW).all()
            assert len(future) == 6
            assert any(event.slots > 0 and event.slots_remaining() == 0 for event in future)
            assert any(event.slots_remaining() > 0 for event in future)
            assert any(event.slots == 0 for event in future)
            assert all(event.slots == 0 or event.target_participants <= event.slots for event in Event.query.all())
            assert {reg.status for reg in Registration.query.all()} == {'pending', 'confirmed', 'completed', 'cancelled'}
            assert {record.status for record in Attendance.query.all()} == {'present', 'absent', 'excused'}
            for reg in Registration.query.all():
                assert reg.registered_at < min(reg.event.date, NOW)
                if reg.attendance_record:
                    assert reg.status == ('completed' if reg.attendance_record.status == 'present' else 'confirmed')
                    assert reg.certificate_eligible == (reg.attendance_record.status == 'present')
                assert not reg.policy_accepted_at  # Do not invent legal consent for preserved accounts.
            for request in CancellationRequest.query.all():
                assert request.requested_at < request.registration.event.cancellation_deadline
                assert request.registration.status == ('cancelled' if request.status == 'approved' else 'confirmed')
                assert bool(request.reviewed_at) == (request.status != 'pending')
                if request.reviewed_by:
                    assert request.reviewed_by.campus_id == request.registration.event.campus_id
            assert {note.is_read for note in Notification.query.all()} == {False, True}
            assert EventAnnouncement.query.count() == 3


def add_old_records():
    student = User.query.filter_by(email='student@psu.edu').one()
    removed = User.query.filter_by(email='faculty@psu.edu').one()
    event = Event.query.first()
    plan = AnnualPlan(source_key='old', year=2025, plan_type='AOP', title='Old plan', source_document='old.csv')
    indicator = AnnualIndicator(source_key='old', plan=plan, code='old', name='Old target',
        program='Old programme', unit='people', responsible_office='Extension Office')
    target = AnnualTarget(source_key='old', indicator=indicator, campus=event.campus, target_value=3)
    db.session.add_all([target, AnnualActivityMapping(target=target, event=event),
        AnnualResult(source_key='old', target=target, result_type='calculated'),
        AnnualGoalProposal(campus_id=event.campus_id, proposed_by_id=removed.id, reviewed_by_id=student.id,
                           payload={}, replaces_target_id=None, history=[]),
        Milestone(event=event, filename='retain-on-disk.pdf', uploaded_by_id=removed.id),
        HistoricalActivity(source_key='old', source_document='old.csv', source_page=1, source_row=1,
                           unit_name='Lingayen', title='Old history'),
        AnalyticsSummary(campus_id=event.campus_id, metric_type='old', value=99, period='2025'),
        RecommendationLog(user_id=removed.id, event_id=event.id, similarity_score=.5),
        Notification(user=removed, title='Old notification', message='Old'),
        SystemSetting(key='retained-setting', value='retain')])
    for model in (TermsRevision, PrivacyRevision, ParticipationAgreementRevision):
        db.session.add(model(title='Retained policy', body='Retained body', version='retained',
                             published_by_id=removed.id, is_active=False))
    db.session.flush()
    for user in (student, removed):
        db.session.add_all([
            TermsAcceptance(user_id=user.id, revision_id=TermsRevision.query.one().id),
            PrivacyAcknowledgement(user_id=user.id, revision_id=PrivacyRevision.query.one().id),
            PasswordResetToken(user=user, token_hash=f'token-{user.id}', expires_at=datetime(2027, 1, 1))])
    student.profile.past_participation = [{'event': 'old'}]
    db.session.commit()


def test_cleans_annual_dependencies_and_preserves_reference_data(app):
    with app.app_context():
        add_old_records()
        retained_names = ['campuses', 'skills', 'interests', 'sdg_goals', 'system_settings']
        before = {name: snapshot()[name] for name in retained_names}
        student = User.query.filter_by(email='student@psu.edu').one()
        profile_id = student.profile.id
    result = invoke(app)
    assert result.exit_code == 0, (result.output, result.exception)
    with app.app_context():
        assert {name: snapshot()[name] for name in retained_names} == before
        assert not AnnualGoalProposal.query.count()
        assert not HistoricalActivity.query.count() and not AnalyticsSummary.query.count()
        assert not Milestone.query.count() and not RecommendationLog.query.count()
        for model in (TermsRevision, PrivacyRevision, ParticipationAgreementRevision):
            assert model.query.one().published_by_id is None
            assert model.query.one().body == 'Retained body'
        student = User.query.filter_by(email='student@psu.edu').one()
        assert student.profile.id == profile_id and student.profile.past_participation == []
        assert TermsAcceptance.query.one().user_id == student.id
        assert PrivacyAcknowledgement.query.one().user_id == student.id
        assert PasswordResetToken.query.one().user_id == student.id


@pytest.mark.parametrize('failure_point', ['_create_accounts', '_create_goals', '_validate_dataset'])
def test_failure_rolls_back_deletes_inserts_and_validation(app, monkeypatch, failure_point):
    with app.app_context():
        add_old_records()
        before = snapshot()
    def fail(*args, **kwargs):
        raise RuntimeError('Injected replacement failure')
    monkeypatch.setattr(f'app.presentation_dataset.{failure_point}', fail)
    result = invoke(app)
    assert result.exit_code != 0
    with app.app_context():
        assert snapshot() == before


def test_default_account_views_and_no_email(app, monkeypatch):
    def fail_email(*args, **kwargs):
        raise AssertionError('The dataset must not send email')
    monkeypatch.setattr('app.services.email.send_email', fail_email)
    result = invoke(app)
    assert result.exit_code == 0, (result.output, result.exception)
    paths = {
        'admin@psu.edu': ('/admin_dash', '/admin/users/export.csv'),
        'student@psu.edu': ('/volunteer_dash', '/opportunities'),
        'director@psu.edu': ('/director_dash', '/analytics', '/annual-goals', '/reports/university.csv'),
        'coordinator@psu.edu': ('/coordinator_dash', '/coordinator_analytics', '/coordinator/cancellation-requests', '/attendance', '/annual-goals'),
    }
    for email, routes in paths.items():
        client = app.test_client()
        with app.app_context():
            user = User.query.filter_by(email=email).one()
            user_id, version = user.id, user.auth_version
        with client.session_transaction() as session:
            session['_user_id'] = str(user_id)
            session['_fresh'] = True
            session['auth_version'] = version
        for path in routes:
            response = client.get(path)
            assert response.status_code == 200, (email, path, response.status_code, response.location)


@pytest.mark.parametrize('code', ['BAYAMBANG', 'STAMARIA', 'ALAMINOS'])
def test_preserves_coordinator_on_campus_without_upcoming_activity(app, code):
    with app.app_context():
        User.query.filter_by(email='coordinator@psu.edu').one().campus_id = Campus.query.filter_by(code=code).one().id
        db.session.commit()
    result = invoke(app)
    assert result.exit_code == 0, (result.output, result.exception)
    with app.app_context():
        coordinator = User.query.filter_by(email='coordinator@psu.edu').one()
        assert coordinator.campus.code == code
        assert CancellationRequest.query.join(Registration).join(Event).filter(
            Event.campus_id == coordinator.campus_id, CancellationRequest.status == 'pending').count() > 0


@pytest.mark.skipif(not os.environ.get('PRESENTATION_TEST_DATABASE_URL'), reason='Requires explicitly supplied empty disposable local MySQL/MariaDB database')
def test_disposable_mariadb_transaction_and_production_guards(app, monkeypatch):
    from app import _seed_campuses, _seed_interests_skills, _seed_sdgs, _seed_events, _seed_users
    url = make_url(os.environ['PRESENTATION_TEST_DATABASE_URL'])
    assert url.host == '127.0.0.1' and url.database.startswith('psu_presentation_test_')
    assert url.get_backend_name() in ('mysql', 'mariadb')
    engine = create_engine(url)
    assert not inspect(engine).get_table_names(), 'Integration target must be empty; never reuse application databases.'
    with app.app_context():
        db.session.remove()
        original_engine = db._app_engines[app][None]
        db._app_engines[app][None] = engine
        try:
            db.create_all()
            for seed in (_seed_campuses, _seed_interests_skills, _seed_sdgs, _seed_events, _seed_users):
                seed(app)
            add_old_records()
            before = snapshot()
            monkeypatch.setenv('RAILWAY_SERVICE_ID', DEMO_SERVICE_ID)
            monkeypatch.setenv('PRESENTATION_DATABASE_HOST', 'wrong-host')
            app.testing = False
            def call(dry_run=False):
                args = ['reset-and-seed-presentation', '--database', url.database]
                if dry_run:
                    args.append('--dry-run')
                return app.test_cli_runner().invoke(args=args, input=f'RESET PRESENTATION 127.0.0.1/{url.database}\n')
            assert 'independently verified' in call().output
            monkeypatch.setenv('PRESENTATION_DATABASE_HOST', '127.0.0.1')
            assert call(True).exit_code == 0
            assert snapshot() == before
            for point in ('_create_accounts', '_create_goals', '_validate_dataset'):
                with monkeypatch.context() as failure:
                    def fail(*args, **kwargs):
                        raise RuntimeError('Injected MariaDB failure')
                    failure.setattr(f'app.presentation_dataset.{point}', fail)
                    assert call().exit_code != 0
                assert snapshot() == before
            for _ in range(2):
                result = call()
                assert result.exit_code == 0, (result.output, result.exception)
                assert User.query.count() == 92 and Event.query.count() == 28
                assert db.session.execute(text('SELECT @@FOREIGN_KEY_CHECKS')).scalar() == 1
                assert summary(2026, Campus.query.filter_by(code='ASINGAN').one().id)['remaining'] == 3
            app.testing = True
        finally:
            db.session.remove()
            engine.dispose()
            db._app_engines[app][None] = original_engine
