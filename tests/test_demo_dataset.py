"""Destructive demo CLI checks use only SQLite with foreign keys enabled."""
from datetime import datetime

import pytest
from sqlalchemy import select

from app import create_app
from app.models import db
from app.models.audit import AuditLog
from app.models.event import (Attendance, CancellationRequest, Campus, Event,
                              EventAnnouncement, ExternalParticipant, Registration,
                              HistoricalActivity, Milestone, RecommendationLog,
                              AnalyticsSummary, event_sdgs, event_skills)
from app.models.notification import Notification
from app.models.policy import (TermsRevision, TermsAcceptance, PrivacyRevision,
                               PrivacyAcknowledgement, ParticipationAgreementRevision)
from app.models.user import User, PasswordResetToken, VolunteerProfile
from app.demo_dataset import DEMO_SERVICE_ID, KEEP


@pytest.fixture
def app():
    instance = create_app('testing')
    with instance.app_context():
        db.session.remove()
        with db.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    yield instance
    with instance.app_context():
        db.session.remove()
        db.engine.dispose()


def invoke(app, confirmation=None, *options):
    return app.test_cli_runner().invoke(
        args=['reset-and-seed-demo', '--database', ':memory:', *options],
        input=confirmation)


def test_refuses_wrong_service_database_account_and_confirmation(app, monkeypatch):
    app.testing = False
    monkeypatch.setenv('RAILWAY_SERVICE_ID', 'main-service')
    assert 'approved Railway demo' in invoke(app).output
    monkeypatch.setenv('RAILWAY_SERVICE_ID', DEMO_SERVICE_ID)
    result = app.test_cli_runner().invoke(args=['reset-and-seed-demo', '--database', 'wrong'])
    assert result.exit_code != 0 and 'does not match' in result.output
    app.testing = True
    with app.app_context():
        count = Event.query.count()
        coordinator = User.query.filter_by(email='coordinator@psu.edu').one()
        coordinator.role = 'volunteer'
        db.session.commit()
    result = invoke(app)
    assert result.exit_code != 0 and 'must have role coordinator' in result.output
    with app.app_context():
        coordinator = User.query.filter_by(email='coordinator@psu.edu').one()
        coordinator.role = 'coordinator'
        db.session.commit()
    assert invoke(app, 'NO\n').exit_code != 0
    # A confirmation copied from the previous, narrower command must not work.
    assert invoke(app, 'RESET DEMO local/:memory:\n').exit_code != 0
    result = invoke(app, None, '--dry-run')
    assert result.exit_code == 0, (result.output, result.exception)
    with app.app_context():
        assert Event.query.count() == count
        assert User.query.count() == 6
    assert 'Remove 3 other accounts' in result.output
    assert 'Reset ALL activity/participation data' in result.output


def test_replacement_counts_links_preservation_repeat_and_rollback(app, monkeypatch):
    with app.app_context():
        passwords = {u.email: (u.id, u.password_hash) for u in User.query.filter(User.email.in_(KEEP)).all()}
        coordinator = User.query.filter_by(email='coordinator@psu.edu').one()
        coordinator.campus_id = None
        old = Event(title='[Demo Analytics] Old fixture', description='old', date=datetime.now())
        db.session.add(old)
        participant = ExternalParticipant(id_number='DEMO-EXT-001', name='Previous fixture')
        registration = Registration(event=old, external_participant=participant)
        db.session.add(Attendance(registration=registration, event=old))
        db.session.commit()
    # Hashing speed is irrelevant to this database transaction test.
    monkeypatch.setattr(User, 'set_password', lambda self, password: setattr(self, 'password_hash', 'test-only-unusable-hash'))
    for iteration in range(2):
        result = invoke(app, 'RESET ALL DEMO local/:memory:\n')
        assert result.exit_code == 0, (result.output, result.exception)
        with app.app_context():
            events = Event.query.all()
            ids = [e.id for e in events]
            assert len(events) == 200
            assert Registration.query.filter(Registration.event_id.in_(ids)).count() == 5000
            assert Attendance.query.filter(Attendance.event_id.in_(ids)).count() == 4000
            assert CancellationRequest.query.count() == 150
            assert ExternalParticipant.query.count() == 200
            assert AuditLog.query.filter_by(action='synthetic_demo_fixture').count() == 200
            assert len(db.session.execute(select(event_sdgs).where(event_sdgs.c.event_id.in_(ids))).all()) == 600
            assert User.query.filter(User.email.like('volunteer-%@demo.invalid')).count() == 749
            assert {u.sex for u in User.query.filter(User.email.like('volunteer-%@demo.invalid')).all()} == {'male', 'female', 'prefer_not_to_say'}
            assert {u.email: (u.id, u.password_hash) for u in User.query.filter(User.email.in_(passwords)).all()} == passwords
            assert all(not e.title.startswith('[Demo') for e in events)
            assert not User.query.filter(User.email.in_(('faculty@psu.edu', 'staff@psu.edu', 'admin@psu.edu'))).count()
            assert User.query.count() == 3 + 749 + Campus.query.count() - 1
            assert User.query.filter_by(email='coordinator@psu.edu').one().campus_id in {c.id for c in Campus.query.all()}
            assert any(e.date > datetime.now() and e.slots_remaining() == 0 and e.slots > 0 for e in events)
            assert any(e.date > datetime.now() and e.slots_remaining() > 0 for e in events)
            assert any(0 < len(e.attendance_records) < len(e.registrations) for e in events)
            assert all(r.registered_at <= datetime.now() for e in events for r in e.registrations)
            assert all(r.registration.status == ('cancelled' if r.status == 'approved' else 'confirmed') for r in CancellationRequest.query.all())
        if iteration == 0:
            client = app.test_client()
            assert client.get('/opportunities').status_code == 200
            for email, paths in (
                ('director@psu.edu', ('/director_dash', '/analytics', '/reports/university.csv')),
                ('coordinator@psu.edu', ('/coordinator_dash', '/coordinator_analytics')),
            ):
                with app.app_context():
                    user = User.query.filter_by(email=email).one()
                    user_id, version = user.id, user.auth_version
                with client.session_transaction() as session:
                    session.clear()
                    session['_user_id'] = str(user_id)
                    session['_fresh'] = True
                    session['auth_version'] = version
                for path in paths:
                    response = client.get(path)
                    assert response.status_code == 200, (path, response.status_code)
    with app.app_context():
        ids_before = {e.id for e in Event.query.all()}
        accounts_before = {u.email: (u.id, u.password_hash) for u in User.query.all()}
    def fail(*args, **kwargs):
        raise RuntimeError('Injected fixture failure')
    monkeypatch.setattr('app._seed_sdgs', fail)
    result = invoke(app, 'RESET ALL DEMO local/:memory:\n')
    assert result.exit_code != 0
    with app.app_context():
        assert {e.id for e in Event.query.all()} == ids_before
        assert Attendance.query.count() == 4000
        assert ExternalParticipant.query.count() == 200
        assert {u.email: (u.id, u.password_hash) for u in User.query.all()} == accounts_before


def test_clears_unmarked_records_but_preserves_main_account_data_and_catalogues(app, monkeypatch):
    with app.app_context():
        other_event = Event.query.first()
        user = User.query.filter_by(email='student@psu.edu').one()
        disposable = User.query.filter_by(email='admin@psu.edu').one()
        other_title = other_event.title
        participant = ExternalParticipant(id_number='UNMARKED-EXT')
        registration = Registration(event=other_event, external_participant=participant)
        db.session.add(registration)
        db.session.add(CancellationRequest(registration=registration, reason='Other'))
        db.session.add(Milestone(event_id=other_event.id, filename='old.pdf', uploaded_by_id=user.id))
        db.session.add(EventAnnouncement(event_id=other_event.id, author_id=user.id,
                                        announcement_type='event_update', message='Old announcement'))
        db.session.add(RecommendationLog(user_id=user.id, event_id=other_event.id, similarity_score=0.5))
        db.session.add(Notification(user_id=user.id, title='Old unrelated notification', message='Old'))
        db.session.add(AuditLog(actor_id=disposable.id, action='old', target_type='event'))
        db.session.add(AnalyticsSummary(campus_id=user.campus_id, metric_type='old', value=100, period='2021'))
        db.session.add(HistoricalActivity(source_key='old', source_document='old.csv',
            source_page=1, source_row=1, unit_name='Test', title='Historical activity', year_conducted=2021))
        terms = TermsRevision(title='Retained terms', body='Terms body', version='kept',
                              published_by_id=disposable.id, is_active=False)
        privacy = PrivacyRevision(title='Retained privacy', body='Privacy body', version='kept',
                                  published_by_id=user.id, is_active=False)
        agreement = ParticipationAgreementRevision(title='Retained agreement', body='Agreement',
            version='kept', published_by_id=disposable.id, is_active=False)
        db.session.add_all([terms, privacy, agreement])
        db.session.flush()
        for account in (user, disposable):
            db.session.add(TermsAcceptance(user_id=account.id, revision_id=terms.id))
            db.session.add(PrivacyAcknowledgement(user_id=account.id, revision_id=privacy.id))
            db.session.add(PasswordResetToken(user_id=account.id, token_hash=f'kept-{account.id}', expires_at=datetime(2099, 1, 1)))
        user.profile.past_participation = [{'event': other_title}]
        db.session.commit()
        preserved_id, preserved_profile = user.id, user.profile.id
        preserved_skills = [s.id for s in user.skills]
        preserved_interests = [i.id for i in user.interests]
        catalogue = {table.name: len(db.session.execute(select(table)).all()) for table in (
            Campus.__table__, db.metadata.tables['skills'], db.metadata.tables['interests'], db.metadata.tables['sdg_goals'])}
    monkeypatch.setattr(User, 'set_password', lambda self, password: setattr(self, 'password_hash', 'test-only-unusable-hash'))
    result = invoke(app, 'RESET ALL DEMO local/:memory:\n')
    assert result.exit_code == 0, (result.output, result.exception)
    with app.app_context():
        assert not Event.query.filter_by(title=other_title).count()
        assert not ExternalParticipant.query.filter_by(id_number='UNMARKED-EXT').count()
        assert not HistoricalActivity.query.count()
        assert not AnalyticsSummary.query.count()
        assert not Milestone.query.count()
        assert not EventAnnouncement.query.count()
        assert not RecommendationLog.query.count()
        assert not Notification.query.filter_by(title='Old unrelated notification').count()
        assert not AuditLog.query.filter_by(action='old').count()
        assert TermsRevision.query.one().body == 'Terms body'
        assert TermsRevision.query.one().published_by_id is None
        assert PrivacyRevision.query.one().published_by_id == preserved_id
        assert ParticipationAgreementRevision.query.one().published_by_id is None
        assert TermsAcceptance.query.one().user_id == preserved_id
        assert PrivacyAcknowledgement.query.one().user_id == preserved_id
        assert PasswordResetToken.query.one().user_id == preserved_id
        user = db.session.get(User, preserved_id)
        assert user.profile.id == preserved_profile
        assert user.profile.past_participation == []
        assert [s.id for s in user.skills] == preserved_skills
        assert [i.id for i in user.interests] == preserved_interests
        assert {name: len(db.session.execute(select(db.metadata.tables[name])).all()) for name in catalogue} == catalogue
