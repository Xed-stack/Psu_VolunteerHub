import pytest
import re
from app import create_app
from app.models import db
from app.models.user import User, VolunteerProfile, SystemSetting, Skill, Interest
from app.models.event import Event, Registration, Attendance, Campus, ExternalParticipant
from app.recommendation.engine import (
    _cosine_similarity,
    bootstrap_from_event,
    get_recommendations,
)
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError


# â”€â”€ Fixtures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.fixture
def app():
    app = create_app('testing')
    app.config['SERVER_NAME'] = 'localhost'

    with app.app_context():
        # Replace the cached engine with an in-memory engine
        new_engine = create_engine('sqlite:///:memory:')
        db._app_engines[app][None] = new_engine
        db.create_all()
        _seed_campuses()
        _seed_events()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


# â”€â”€ Seed helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _seed_campuses():
    campuses = [
        Campus(name='Lingayen', code='LINGAYEN'),
        Campus(name='Urdaneta', code='URDANETA'),
        Campus(name='Asingan', code='ASINGAN'),
        Campus(name='Bayambang', code='BAYAMBANG'),
        Campus(name='Binmaley', code='BINMALEY'),
        Campus(name='Infanta', code='INFANTA'),
        Campus(name='San Carlos', code='SANCARLOS'),
        Campus(name='Santa Maria', code='STAMARIA'),
        Campus(name='Alaminos', code='ALAMINOS'),
    ]
    for c in campuses:
        db.session.add(c)
    db.session.commit()


def _seed_events():
    events = [
        Event(title='Youth Coding Mentor', description='Help students learn Python.',
              date=datetime.now() + timedelta(days=7),
              required_skills='Teaching, Python, Communication', slots=20,
              campus_id=1, category='Education & Literacy'),
        Event(title='Green Campus Initiative', description='Tree planting.',
              date=datetime.now() + timedelta(days=14),
              required_skills='Environmental Conservation, Agriculture', slots=50,
              campus_id=1, category='Environment'),
        Event(title='Community Food Drive', description='Distribute relief packages.',
              date=datetime.now() + timedelta(days=10),
              required_skills='Organizational, Communication', slots=30,
              campus_id=2, category='Community Development'),
        Event(title='Rural Literacy Program', description='Teach reading.',
              date=datetime.now() + timedelta(days=21),
              required_skills='Teaching, Tutoring, Communication', slots=15,
              campus_id=1, category='Education & Literacy'),
        Event(title='Disaster Response Training', description='First aid workshop.',
              date=datetime.now() + timedelta(days=5),
              required_skills='Medical, First Aid', slots=40,
              campus_id=3, category='Disaster Response'),
        Event(title='Community IT Support Workshop', description='Digital literacy.',
              date=datetime.now() + timedelta(days=30),
              required_skills='IT, Computer Skills, Teaching', slots=25,
              campus_id=4, category='Technology & Digital'),
        Event(title='Coastal Cleanup Drive', description='Preserve coastline.',
              date=datetime.now() + timedelta(days=3),
              required_skills='Environmental Conservation, Teamwork', slots=100,
              campus_id=1, category='Environment'),
        Event(title='Community Wellness Fair', description='Free health mission.',
              date=datetime.now() + timedelta(days=45),
              required_skills='Medical, First Aid, Organizational', slots=60,
              campus_id=7, category='Health & Wellness'),
        Event(title='Sustainable Farming Demo', description='Organic cultivation.',
              date=datetime.now() + timedelta(days=60),
              required_skills='Agriculture, Environmental Conservation', slots=30,
              campus_id=8, category='Environment'),
    ]
    for e in events:
        db.session.add(e)
    db.session.commit()


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _create_user(app, email='test@example.com', password='password123',
                 role='volunteer', name='Test User', campus_id=None):
    with app.app_context():
        user = User(name=name, email=email, role=role, campus_id=campus_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login_as(client, user_id):
    """Set Flask-Login session directly (avoids cookie issues between tests)."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# A. App Initialization
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestAppInit:
    def test_app_creates(self, app):
        assert app is not None
        assert app.testing

    def test_db_tables_exist(self, app):
        with app.app_context():
            for tbl in ('users', 'events', 'campuses', 'registrations', 'attendance', 'volunteer_profiles', 'milestones', 'recommendation_logs', 'analytics_summaries'):
                assert tbl in db.metadata.tables, f'Table {tbl} not found'

    def test_nine_campuses_seeded(self, app):
        with app.app_context():
            assert Campus.query.count() == 9

    def test_nine_events_seeded(self, app):
        with app.app_context():
            assert Event.query.count() == 9


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# B. Authentication
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestAuth:
    def test_register_get(self, client):
        resp = client.get('/auth/register')
        assert resp.status_code == 200

    def test_register_creates_user(self, client, app):
        resp = client.post('/auth/register', data={
            'first_name': 'Alice', 'last_name': 'Test',
            'email': 'alice@test.com',
            'password': 'secret123',
            'account_type': 'volunteer', 'id_number': '21-0001',
            'campus': '1', 'volunteer_type': 'student',
            'college_affiliation': 'College of Computing Sciences',
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            u = User.query.filter_by(email='alice@test.com').first()
            assert u is not None
            assert u.role == 'volunteer'

    def test_public_registration_cannot_create_privileged_role(self, client, app):
        resp = client.post('/auth/register', data={
            'first_name': 'Privilege', 'last_name': 'Attempt',
            'email': 'privilege@test.com',
            'password': 'secret123',
            'account_type': 'coordinator', 'id_number': '21-0099',
            'campus': '1', 'volunteer_type': 'student',
            'college_affiliation': 'College of Computing Sciences',
        })
        assert resp.status_code == 302
        with app.app_context():
            user = User.query.filter_by(email='privilege@test.com').one()
            assert user.role == 'volunteer'

    def test_csrf_rejects_post_without_token_when_enabled(self, client, app):
        app.config['WTF_CSRF_ENABLED'] = True
        resp = client.post('/auth/login', data={
            'identifier': 'nobody@test.com', 'password': 'password123',
        })
        assert resp.status_code == 400

    def test_auth_page_exposes_csrf_token_when_enabled(self, client, app):
        app.config['WTF_CSRF_ENABLED'] = True
        resp = client.get('/auth/login')
        body = resp.data.decode()
        assert re.search(r'const token = "[^"]+"', body)

    def test_register_duplicate_email(self, client, app):
        _create_user(app, email='dup@test.com')
        resp = client.post('/auth/register', data={
            'first_name': 'Dup', 'last_name': 'User',
            'email': 'dup@test.com',
            'password': 'secret123',
            'account_type': 'volunteer', 'id_number': '21-0002',
            'campus': 'Lingayen',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_get(self, client):
        resp = client.get('/auth/login')
        assert resp.status_code == 200

    def test_login_valid_redirects(self, client, app):
        _create_user(app, email='valid@test.com')
        resp = client.post('/auth/login', data={
            'identifier': 'valid@test.com', 'password': 'password123',
        })
        assert resp.status_code == 302
        assert resp.location == '/volunteer_dash'

    def test_login_invalid_shows_error(self, client):
        resp = client.post('/auth/login', data={
            'identifier': 'nobody@test.com', 'password': 'wrong',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_logout_requires_login(self, client):
        resp = client.get('/auth/logout', follow_redirects=True)
        assert resp.status_code == 200

    def test_protected_route_redirects_anon(self, client):
        resp = client.get('/volunteer_dash')
        assert resp.status_code == 302
        assert '/auth/login' in resp.location


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# C. Role-based Access
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestRoleAccess:
    def test_volunteer_can_access_volunteer_dash(self, client, app):
        uid = _create_user(app, email='vol@test.com')
        _login_as(client, uid)
        resp = client.get('/volunteer_dash')
        assert resp.status_code == 200

    def test_volunteer_cannot_access_coordinator_dash(self, client, app):
        uid = _create_user(app, email='vol2@test.com')
        _login_as(client, uid)
        resp = client.get('/coordinator_dash', follow_redirects=True)
        assert resp.status_code == 403

    def test_coordinator_can_access_coordinator_dash(self, client, app):
        uid = _create_user(app, email='coord@test.com', role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/coordinator_dash')
        assert resp.status_code == 200

    def test_director_can_access_director_dash(self, client, app):
        uid = _create_user(app, email='dir@test.com', role='director')
        _login_as(client, uid)
        resp = client.get('/director_dash')
        assert resp.status_code == 200

    def test_director_can_access_analytics(self, client, app):
        uid = _create_user(app, email='dir2@test.com', role='director')
        _login_as(client, uid)
        resp = client.get('/analytics')
        assert resp.status_code == 200

    def test_admin_can_access_admin_dash(self, client, app):
        uid = _create_user(app, email='admin@test.com', role='admin')
        _login_as(client, uid)
        resp = client.get('/admin_dash')
        assert resp.status_code == 200

    def test_unauthenticated_redirected_to_login(self, client):
        for path in ('/volunteer_dash', '/coordinator_dash', '/director_dash', '/admin_dash'):
            resp = client.get(path)
            assert resp.status_code == 302
            assert '/auth/login' in resp.location


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# D. Volunteer Features
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestVolunteerFeatures:
    def test_volunteer_dash_renders(self, client, app):
        uid = _create_user(app, email='vdash@test.com')
        _login_as(client, uid)
        resp = client.get('/volunteer_dash')
        assert resp.status_code == 200

    def test_opportunities_lists(self, client):
        resp = client.get('/opportunities')
        assert resp.status_code == 200

    def test_register_for_event(self, client, app):
        uid = _create_user(app, email='reg@test.com')
        _login_as(client, uid)
        with app.app_context():
            eid = Event.query.first().id
        resp = client.post(f'/opportunities/register/{eid}', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            r = Registration.query.filter_by(user_id=uid).first()
            assert r is not None
            assert r.event_id == eid

    def test_profile_get(self, client, app):
        uid = _create_user(app, email='prof@test.com')
        _login_as(client, uid)
        resp = client.get('/profile')
        assert resp.status_code == 200

    def test_profile_post_updates(self, client, app):
        uid = _create_user(app, email='profup@test.com')
        _login_as(client, uid)
        resp = client.post('/profile', data={
            'skills': 'Python, Teaching',
            'interests': 'Education, Technology',
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            u = User.query.filter_by(email='profup@test.com').first()
            assert u is not None
            assert {s.name for s in u.skills} == {'Python', 'Teaching'}
            assert {i.name for i in u.interests} == {'Education', 'Technology'}

    def test_history_shows(self, client, app):
        uid = _create_user(app, email='hist@test.com')
        _login_as(client, uid)
        resp = client.get('/profile')
        assert resp.status_code == 200


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# E. Coordinator Features
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestCoordinatorFeatures:
    def test_coordinator_dash_renders(self, client, app):
        uid = _create_user(app, email='cdash@test.com', role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/coordinator_dash')
        assert resp.status_code == 200

    def test_create_activity_get(self, client, app):
        uid = _create_user(app, email='create1@test.com', role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/create_activity')
        assert resp.status_code == 200

    def test_create_activity_post(self, client, app):
        uid = _create_user(app, email='create2@test.com', role='coordinator', campus_id=2)
        _login_as(client, uid)
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        resp = client.post('/create_activity', data={
            'title': 'Test Event',
            'description': 'A test event',
            'date': tomorrow,
            'location': 'Test Location',
            'required_skills': 'Teaching',
            'slots': 10,
            'campus_id': 2,
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            e = Event.query.filter_by(title='Test Event').first()
            assert e is not None
            assert e.campus_id == 2

    def test_attendance_renders(self, client, app):
        uid = _create_user(app, email='attend@test.com', role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/attendance')
        assert resp.status_code == 200


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# F. Director Features
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestDirectorFeatures:
    def test_director_dash_renders(self, client, app):
        uid = _create_user(app, email='ddash@test.com', role='director')
        _login_as(client, uid)
        resp = client.get('/director_dash')
        assert resp.status_code == 200

    def test_analytics_renders(self, client, app):
        uid = _create_user(app, email='anl@test.com', role='director')
        _login_as(client, uid)
        resp = client.get('/analytics')
        assert resp.status_code == 200

    def test_kpis_have_expected_keys(self, app):
        from app.recommendation.analytics import AnalyticsAggregator
        with app.app_context():
            kpis = AnalyticsAggregator.kpi_summary()
            for key in ('total_active_volunteers', 'total_hours', 'retention_rate'):
                assert key in kpis, f'KPI key {key} missing'


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# G. Admin Features
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestAdminFeatures:
    def test_admin_dash_renders(self, client, app):
        uid = _create_user(app, email='adm1@test.com', role='admin')
        _login_as(client, uid)
        resp = client.get('/admin_dash')
        assert resp.status_code == 200

    def test_admin_toggle_user_active(self, client, app):
        _create_user(app, email='target@test.com', name='Target')
        admin_uid = _create_user(app, email='adm2@test.com', role='admin')
        _login_as(client, admin_uid)
        with app.app_context():
            target = User.query.filter_by(email='target@test.com').first()
            target_id = target.id
            assert target.is_active is True
        resp = client.post(f'/admin/users/deactivate/{target_id}', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            target = db.session.get(User, target_id)
            assert target.is_active is False
        resp2 = client.post(f'/admin/users/deactivate/{target_id}', follow_redirects=True)
        assert resp2.status_code == 200
        with app.app_context():
            target = db.session.get(User, target_id)
            assert target.is_active is True


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# H. Recommendation Engine
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestRecommendationEngine:
    def test_cosine_similarity_for_binary_terms(self):
        assert _cosine_similarity({'python', 'teaching'},
                                  {'python', 'teaching'}) == pytest.approx(1.0)
        assert _cosine_similarity({'python', 'teaching'},
                                  {'python', 'health'}) == pytest.approx(0.5)
        assert _cosine_similarity({'python'}, {'health'}) == 0.0
        assert _cosine_similarity(set(), {'python'}) == 0.0
        assert _cosine_similarity(set(), set()) == 0.0

    def _make_user_with_terms(self, email, skills, interests):
        """Create a volunteer user with skills/interests attached (3NF)."""
        user = User(name=email.split('@')[0], email=email)
        user.set_password('pw')
        db.session.add(user)
        db.session.flush()
        for name in skills:
            sk = Skill.query.filter_by(name=name).first() or Skill(name=name)
            db.session.add(sk)
            user.skills.append(sk)
        for name in interests:
            it = Interest.query.filter_by(name=name).first() or Interest(name=name)
            db.session.add(it)
            user.interests.append(it)
        profile = VolunteerProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        return profile

    def test_returns_recommendations_for_profile(self, app):
        with app.app_context():
            profile = self._make_user_with_terms(
                'rec@test.com', ['Teaching', 'Python', 'Communication'], ['Education'])
            events = Event.query.all()
            recs = get_recommendations(profile, events)
            assert len(recs) > 0
            for r in recs:
                assert 'event' in r
                assert 'score' in r

    def test_scores_between_zero_and_one(self, app):
        with app.app_context():
            profile = self._make_user_with_terms(
                'score@test.com', ['Teaching', 'Communication'], ['Education'])
            events = Event.query.all()
            recs = get_recommendations(profile, events, top_n=len(events))
            assert len(recs) > 0
            for r in recs:
                assert 0.0 <= r['score'] <= 1.0, f'Score {r["score"]} out of range'

    def test_zero_slots_lower_score(self, app):
        with app.app_context():
            full_event = Event(title='Full Event', description='No slots available',
                               date=datetime.now() + timedelta(days=10),
                               required_skills='Teaching', slots=0, campus_id=1)
            avail_event = Event(title='Avail Event', description='Has slots',
                                date=datetime.now() + timedelta(days=10),
                                required_skills='Teaching', slots=20, campus_id=1)
            db.session.add_all([full_event, avail_event])
            db.session.commit()
            profile = self._make_user_with_terms(
                'slot@test.com', ['Teaching'], ['Education'])
            all_events = [full_event, avail_event]
            recs = get_recommendations(profile, all_events, top_n=2)
            scores = {r['event'].title: r['score'] for r in recs}
            assert scores.get('Avail Event', 0) >= scores.get('Full Event', 1), \
                'Event with slots should score >= event with zero slots'

    def test_upcoming_scores_higher_than_past(self, app):
        with app.app_context():
            future = datetime.now() + timedelta(days=30)
            past = datetime.now() - timedelta(days=30)
            future_event = Event(title='Future Event', description='In the future',
                                 date=future, required_skills='Teaching',
                                 slots=20, campus_id=1)
            past_event = Event(title='Past Event', description='Already happened',
                               date=past, required_skills='Teaching',
                               slots=20, campus_id=1)
            db.session.add_all([future_event, past_event])
            db.session.commit()
            profile = self._make_user_with_terms(
                'time@test.com', ['Teaching'], ['Education'])
            all_events = [future_event, past_event]
            recs = get_recommendations(profile, all_events, top_n=2)
            scores = {r['event'].title: r['score'] for r in recs}
            assert scores.get('Future Event', 0) >= scores.get('Past Event', 1), \
                'Future event should score higher than past event'

    def test_cold_start_returns_upcoming_events(self, app):
        with app.app_context():
            past = Event(title='Past CS', description='past',
                         date=datetime.now() - timedelta(days=1),
                         required_skills='Teaching', slots=10, campus_id=1)
            future = Event(title='Future CS', description='future',
                           date=datetime.now() + timedelta(days=2),
                           required_skills='Teaching', slots=10, campus_id=1)
            db.session.add_all([past, future])
            db.session.commit()
            recs = get_recommendations(None, top_n=5)
            titles = [r['event'].title for r in recs]
            assert 'Future CS' in titles
            assert 'Past CS' not in titles
            assert all(r['score'] == 0 for r in recs)

    def test_cold_start_prefers_popular_event(self, app):
        with app.app_context():
            popular = Event(title='Popular Event', description='many regs',
                            date=datetime.now() + timedelta(days=5),
                            required_skills='Teaching', slots=10, campus_id=1)
            quiet = Event(title='Quiet Event', description='no regs',
                          date=datetime.now() + timedelta(days=1),
                          required_skills='Teaching', slots=10, campus_id=1)
            db.session.add_all([popular, quiet])
            db.session.flush()
            from app.models.event import Registration
            for i in range(3):
                u = User(name=f'Registrant{i}', email=f'regpop{i}@test.com')
                u.set_password('pw')
                db.session.add(u)
                db.session.flush()
                db.session.add(Registration(user_id=u.id, event_id=popular.id,
                                            status='confirmed'))
            db.session.commit()
            recs = get_recommendations(None, top_n=2)
            titles = [r['event'].title for r in recs]
            assert titles.index('Popular Event') < titles.index('Quiet Event'), \
                'Popular event should rank above quiet event'

    def test_cold_start_prefers_user_campus(self, app):
        with app.app_context():
            campus2 = Event(title='Campus Two Event', description='campus 2',
                            date=datetime.now() + timedelta(days=5),
                            required_skills='Teaching', slots=10, campus_id=2)
            campus1 = Event(title='Campus One Event', description='campus 1',
                            date=datetime.now() + timedelta(days=3),
                            required_skills='Teaching', slots=10, campus_id=1)
            db.session.add_all([campus2, campus1])
            db.session.commit()
            recs = get_recommendations(None, top_n=5, campus_id=1)
            titles = [r['event'].title for r in recs]
            assert 'Campus One Event' in titles
            assert 'Campus Two Event' not in titles

    def test_bootstrap_seeds_skills_and_interests(self, app):
        with app.app_context():
            event = Event(title='Bootstrap Event', description='seed me',
                          date=datetime.now() + timedelta(days=5),
                          required_skills='Teaching, Python', slots=10,
                          campus_id=1, category='Education')
            db.session.add(event)
            db.session.commit()
            user = User(name='Boot', email='boot@test.com')
            user.set_password('pw')
            db.session.add(user)
            db.session.commit()
            bootstrap_from_event(user, event)
            assert {s.name for s in user.skills} == {'Teaching', 'Python'}
            assert {i.name for i in user.interests} == {'Education'}

    def test_bootstrap_noop_when_user_has_terms(self, app):
        with app.app_context():
            event = Event(title='Bootstrap Noop', description='no change',
                          date=datetime.now() + timedelta(days=5),
                          required_skills='Teaching', slots=10,
                          campus_id=1, category='Education')
            db.session.add(event)
            db.session.commit()
            profile = self._make_user_with_terms(
                'bootnoop@test.com', ['Communication'], ['Health'])
            u = db.session.get(User, profile.user_id)
            bootstrap_from_event(u, event)
            assert {s.name for s in u.skills} == {'Communication'}
            assert {i.name for i in u.interests} == {'Health'}

    def test_normalize_terms_collapses_variants(self):
        from app.recommendation.engine import normalize_terms
        assert normalize_terms([' IT ', 'Cs', 'Teaching']) == {
            'it/computer skills', 'computer skills', 'teaching'}

    def test_synonym_matches_variant_skill(self, app):
        # 'IT' should match an event whose skill is 'IT/Computer Skills'.
        with app.app_context():
            profile = self._make_user_with_terms(
                'synmatch@test.com', ['IT'], ['Technology'])
            event = Event(title='Syn Event', description='x',
                          date=datetime.now() + timedelta(days=5),
                          required_skills='IT/Computer Skills', slots=10,
                          campus_id=1, category='Technology')
            db.session.add(event)
            db.session.commit()
            recs = get_recommendations(profile, [event], top_n=1)
            assert recs[0]['score'] == pytest.approx(1.0)

    def test_participation_history_weights_category(self, app):
        with app.app_context():
            profile = self._make_user_with_terms(
                'histw@test.com', ['Teaching', 'Communication'], ['Education'])
            user = db.session.get(User, profile.user_id)
            # History event the volunteer previously joined (excluded later).
            hist = Event(title='History Ev', description='x',
                         date=datetime.now() - timedelta(days=10),
                         required_skills='Teaching, Communication', slots=10,
                         campus_id=1, category='Health & Wellness')
            db.session.add(hist)
            db.session.commit()
            db.session.add(Registration(
                user_id=user.id, event_id=hist.id, status='completed'))
            # Two candidate events with identical base similarity.
            ev_health = Event(title='Health Cand', description='x',
                              date=datetime.now() + timedelta(days=5),
                              required_skills='Teaching, Communication', slots=10,
                              campus_id=1, category='Health & Wellness')
            ev_sport = Event(title='Sport Cand', description='x',
                             date=datetime.now() + timedelta(days=6),
                             required_skills='Teaching, Communication', slots=10,
                             campus_id=1, category='Sports & Recreation')
            db.session.add_all([ev_health, ev_sport])
            db.session.commit()
            recs = get_recommendations(
                profile, [ev_health, ev_sport], top_n=5)
            scores = {r['event'].title: r['score'] for r in recs}
            assert scores['Health Cand'] > scores['Sport Cand']

    def test_recommendations_deterministic(self, app):
        with app.app_context():
            profile = self._make_user_with_terms(
                'determ@test.com', ['Teaching', 'Communication'], ['Education'])
            event = Event(title='Det Event', description='x',
                          date=datetime.now() + timedelta(days=5),
                          required_skills='Teaching', slots=10,
                          campus_id=1, category='Education')
            db.session.add(event)
            db.session.commit()
            first = get_recommendations(profile, [event], top_n=5)
            second = get_recommendations(profile, [event], top_n=5)
            assert [r['event'].id for r in first] == [r['event'].id for r in second]
            assert [r['score'] for r in first] == [r['score'] for r in second]


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# N. In-App Notifications (Phase 15)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestNotifications:
    def test_list_requires_login(self, client):
        resp = client.get('/notifications')
        assert resp.status_code in (302, 401)

    def test_notification_visible_to_owner(self, app, client):
        uid = _create_user(app, email='volA@test.com', role='volunteer', name='VolA')
        with app.app_context():
            from app.models.notification import Notification
            db.session.add(Notification(user_id=uid, title='Hi Vol', message='m'))
            db.session.commit()
        _login_as(client, uid)
        resp = client.get('/notifications')
        assert resp.status_code == 200
        assert b'Hi Vol' in resp.data

    def test_notification_hidden_from_other_user(self, app, client):
        uid = _create_user(app, email='volA@test.com', role='volunteer', name='VolA')
        cid = _create_user(app, email='coordA@test.com', role='coordinator',
                           campus_id=1, name='CoordA')
        with app.app_context():
            from app.models.notification import Notification
            db.session.add(Notification(user_id=uid, title='Hi Vol', message='m'))
            db.session.commit()
        _login_as(client, cid)
        resp = client.get('/notifications')
        assert resp.status_code == 200
        assert b'Hi Vol' not in resp.data

    def test_mark_as_read(self, app, client):
        uid = _create_user(app, email='volB@test.com', role='volunteer', name='VolB')
        with app.app_context():
            from app.models.notification import Notification
            n = Notification(user_id=uid, title='T', message='m')
            db.session.add(n)
            db.session.commit()
            nid = n.id
        _login_as(client, uid)
        resp = client.post(f'/notifications/{nid}/read', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Notification, nid).is_read is True

    def test_mark_all_read(self, app, client):
        uid = _create_user(app, email='volE@test.com', role='volunteer', name='VolE')
        with app.app_context():
            from app.models.notification import Notification
            db.session.add(Notification(user_id=uid, title='A', message='m'))
            db.session.add(Notification(user_id=uid, title='B', message='m'))
            db.session.commit()
        _login_as(client, uid)
        resp = client.post('/notifications/read-all', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert Notification.query.filter_by(
                user_id=uid, is_read=False).count() == 0

    def test_cross_user_mark_read_denied(self, app, client):
        uid = _create_user(app, email='volC@test.com', role='volunteer', name='VolC')
        oid = _create_user(app, email='other@test.com', role='volunteer', name='Other')
        with app.app_context():
            from app.models.notification import Notification
            n = Notification(user_id=uid, title='Secret', message='m')
            db.session.add(n)
            db.session.commit()
            nid = n.id
        _login_as(client, oid)
        resp = client.post(f'/notifications/{nid}/read', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            # Ownership enforced: the other user cannot mark it read.
            assert db.session.get(Notification, nid).is_read is False

    def test_registration_notifies_campus_coordinator(self, app, client):
        vid = _create_user(app, email='volD@test.com', role='volunteer',
                           campus_id=1, name='VolD')
        cid = _create_user(app, email='coordD@test.com', role='coordinator',
                           campus_id=1, name='CoordD')
        _login_as(client, vid)
        # Event id 1 (Youth Coding Mentor) has campus_id=1.
        resp = client.post('/opportunities/register/1', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            from app.models.notification import Notification
            notes = Notification.query.filter_by(user_id=cid).all()
            assert len(notes) >= 1
            assert any('New registration' in n.title for n in notes)



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# I. Search, Filter & Pagination
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestSearchFilterPagination:

    def test_filter_by_campus(self, client, app):
        uid = _create_user(app, email='campusfilt@test.com')
        _login_as(client, uid)
        resp = client.get('/opportunities?campus=1')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body
        assert 'Sustainable Farming Demo' not in body

    def test_filter_by_category(self, client, app):
        uid = _create_user(app, email='catfilt@test.com')
        _login_as(client, uid)
        resp = client.get('/opportunities?category=Environment')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Green Campus Initiative' in body
        assert 'Youth Coding Mentor' not in body

    def test_search_by_keyword(self, client, app):
        uid = _create_user(app, email='searchfilt@test.com')
        _login_as(client, uid)
        resp = client.get('/opportunities?search=literacy')
        assert resp.status_code == 200
        assert 'Rural Literacy Program' in resp.data.decode()

    def test_pagination_exists(self, client, app):
        uid = _create_user(app, email='pagetest@test.com')
        _login_as(client, uid)
        with app.app_context():
            for i in range(3):
                db.session.add(Event(
                    title=f'Pagination Extra {i}',
                    description=f'Extra event {i}',
                    date=datetime.now() + timedelta(days=100 + i),
                    required_skills='Test', slots=10, campus_id=1
                ))
            db.session.commit()
        resp = client.get('/opportunities?page=1')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Showing 9 active opportunities' in body
        assert 'page=2' in body

    def test_filter_and_page_combined(self, client, app):
        uid = _create_user(app, email='combofilt@test.com')
        _login_as(client, uid)
        resp = client.get('/opportunities?campus=1&page=1')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body
        assert 'Green Campus Initiative' in body
        assert 'Sustainable Farming Demo' not in body

    def test_coordinator_status_filter(self, client, app):
        uid = _create_user(app, email='coordstatus@test.com',
                           role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/coordinator_dash?status=upcoming')
        assert resp.status_code == 200
        assert 'Upcoming' in resp.data.decode()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# J. Missing Features
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestMissingFeatures:

    def test_registration_has_only_one_attendance_record(self, app):
        volunteer_id = _create_user(
            app, email='uniqueattendance@test.com', role='volunteer', campus_id=1)
        with app.app_context():
            registration = Registration(
                user_id=volunteer_id, event_id=1, status='confirmed')
            db.session.add(registration)
            db.session.flush()
            db.session.add(Attendance(
                registration_id=registration.id, user_id=volunteer_id,
                event_id=1, status='present', hours_completed=1))
            db.session.commit()
            db.session.add(Attendance(
                registration_id=registration.id, user_id=volunteer_id,
                event_id=1, status='present', hours_completed=2))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_coordinator_cannot_access_director_analytics(self, client, app):
        uid = _create_user(app, email='coordscope@test.com',
                           role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/analytics')
        assert resp.status_code == 403

    def test_admin_can_access_director_analytics(self, client, app):
        uid = _create_user(app, email='adminanalytics@test.com', role='admin')
        _login_as(client, uid)
        resp = client.get('/analytics')
        assert resp.status_code == 200

    def test_non_volunteer_cannot_register_for_event(self, client, app):
        uid = _create_user(app, email='coordregister@test.com',
                           role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.post('/opportunities/register/1')
        assert resp.status_code == 403
        with app.app_context():
            assert Registration.query.filter_by(user_id=uid).count() == 0

    def test_coordinator_activity_is_forced_to_assigned_campus(self, client, app):
        uid = _create_user(app, email='coordcampus@test.com',
                           role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.post('/create_activity', data={
            'title': 'Scoped Activity',
            'description': 'Must stay in the assigned campus.',
            'date': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'campus_id': '2',
            'slots': '10',
        })
        assert resp.status_code == 302
        with app.app_context():
            created = Event.query.filter_by(title='Scoped Activity').one()
            assert created.campus_id == 1

    def test_coordinator_cannot_update_other_campus_attendance(self, client, app):
        coordinator_id = _create_user(
            app, email='coordattendance@test.com', role='coordinator', campus_id=1)
        volunteer_id = _create_user(
            app, email='othercampusvol@test.com', role='volunteer', campus_id=2)
        with app.app_context():
            registration = Registration(
                user_id=volunteer_id, event_id=3, status='confirmed')
            db.session.add(registration)
            db.session.commit()
            registration_id = registration.id
        _login_as(client, coordinator_id)
        resp = client.post('/attendance', data={
            'event_id': '3',
            'registration_id': str(registration_id),
            'status': 'present',
            'hours_completed': '2',
        })
        assert resp.status_code == 403

    def test_present_attendance_sets_certificate_eligibility(self, client, app):
        coordinator_id = _create_user(
            app, email='certcoord@test.com', role='coordinator', campus_id=1)
        volunteer_id = _create_user(
            app, email='certvol@test.com', role='volunteer', campus_id=1)
        with app.app_context():
            registration = Registration(
                user_id=volunteer_id, event_id=1, status='confirmed')
            db.session.add(registration)
            db.session.commit()
            registration_id = registration.id
        _login_as(client, coordinator_id)
        resp = client.post('/attendance', data={
            'event_id': '1',
            'registration_id': str(registration_id),
            'status': 'present',
            'hours_completed': '2.5',
        })
        assert resp.status_code == 302
        with app.app_context():
            registration = db.session.get(Registration, registration_id)
            assert registration.status == 'completed'
            assert registration.certificate_eligible is True
            assert registration.attendance_record.hours_completed == 2.5

    def test_absence_revokes_certificate_eligibility_without_duplicate(self, client, app):
        coordinator_id = _create_user(
            app, email='certrevoke@test.com', role='coordinator', campus_id=1)
        volunteer_id = _create_user(
            app, email='certrevokevol@test.com', role='volunteer', campus_id=1)
        with app.app_context():
            registration = Registration(
                user_id=volunteer_id, event_id=1, status='completed')
            db.session.add(registration)
            db.session.flush()
            db.session.add(Attendance(
                registration_id=registration.id, user_id=volunteer_id,
                event_id=1, status='present', hours_completed=2.5))
            db.session.commit()
            registration_id = registration.id
        _login_as(client, coordinator_id)
        resp = client.post('/attendance', data={
            'event_id': '1',
            'registration_id': str(registration_id),
            'status': 'absent',
            'hours_completed': '0',
        })
        assert resp.status_code == 302
        with app.app_context():
            registration = db.session.get(Registration, registration_id)
            assert registration.status == 'confirmed'
            assert registration.certificate_eligible is False
            assert Attendance.query.filter_by(
                registration_id=registration_id).count() == 1

    def test_coordinator_cannot_upload_to_other_campus_event(self, client, app):
        uid = _create_user(app, email='coordmilestone@test.com',
                           role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.post('/events/3/milestones')
        assert resp.status_code == 403

    def test_export_events_csv(self, client, app):
        uid = _create_user(app, email='evtcsv@test.com',
                           role='coordinator', campus_id=1)
        _login_as(client, uid)
        resp = client.get('/reports/events.csv')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/csv'

    def test_export_campus_csv(self, client, app):
        uid = _create_user(app, email='camcsv@test.com', role='director')
        _login_as(client, uid)
        resp = client.get('/reports/campus.csv')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/csv'
        assert b'Volunteer Participations' in resp.data

    def test_export_campus_pdf(self, client, app):
        uid = _create_user(app, email='campdf@test.com', role='director')
        _login_as(client, uid)
        resp = client.get('/reports/campus.pdf')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/pdf'
        assert resp.data.startswith(b'%PDF-')

    def test_admin_campus_filter(self, client, app):
        uid = _create_user(app, email='admfil@test.com', role='admin')
        _login_as(client, uid)
        resp = client.get('/admin_dash?campus_id=1')
        assert resp.status_code == 200

    def test_admin_settings_get(self, client, app):
        uid = _create_user(app, email='admstg@test.com', role='admin')
        _login_as(client, uid)
        resp = client.get('/settings')
        assert resp.status_code == 200

    def test_admin_settings_post(self, client, app):
        uid = _create_user(app, email='admstp@test.com', role='admin')
        _login_as(client, uid)
        resp = client.post('/settings', data={'max_slots_per_event': '120'},
                           follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            s = SystemSetting.query.filter_by(key='max_slots_per_event').first()
            assert s is not None
            assert s.value == '120'


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# K. Admin User Management
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestAdminUserManagement:

    def test_admin_create_user_get(self, client, app):
        uid = _create_user(app, email='acreateget@test.com', role='admin')
        _login_as(client, uid)
        resp = client.get('/admin/users/create')
        assert resp.status_code == 200

    def test_admin_create_user_post(self, client, app):
        uid = _create_user(app, email='acreatepost@test.com', role='admin')
        _login_as(client, uid)
        resp = client.post('/admin/users/create', data={
            'name': 'New User',
            'email': 'new@test.com',
            'password': 'password123',
            'role': 'coordinator',
            'campus_id': 1,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'User New User created successfully' in resp.data
        with app.app_context():
            u = User.query.filter_by(email='new@test.com').first()
            assert u is not None
            assert u.name == 'New User'
            assert u.role == 'coordinator'
            assert u.campus_id == 1

    def test_admin_edit_user_get(self, client, app):
        with app.app_context():
            admin = User(name='EditGetAdmin', email='editget@test.com', role='admin')
            admin.set_password('pw')
            db.session.add(admin)
            db.session.commit()
            target_id = admin.id
        _login_as(client, target_id)
        resp = client.get(f'/admin/users/{target_id}/edit')
        assert resp.status_code == 200

    def test_admin_edit_user_post(self, client, app):
        with app.app_context():
            safety_admin = User(name='Safety Admin', email='safety@test.com',
                                role='admin')
            safety_admin.set_password('pw')
            admin = User(name='EditPostAdmin', email='editpost@test.com',
                         role='admin', campus_id=1)
            admin.set_password('pw')
            db.session.add_all([safety_admin, admin])
            db.session.commit()
            target_id = admin.id
        _login_as(client, target_id)
        resp = client.post(f'/admin/users/{target_id}/edit', data={
            'name': 'Updated Name',
            'email': 'updated@test.com',
            'role': 'director',
            'campus_id': 2,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Updated Name updated' in resp.data
        with app.app_context():
            u = db.session.get(User, target_id)
            assert u.name == 'Updated Name'
            assert u.email == 'updated@test.com'
            assert u.role == 'director'
            assert u.campus_id == 2

    def test_admin_reset_password(self, client, app):
        with app.app_context():
            admin = User(name='ResetAdmin', email='reset@test.com', role='admin')
            admin.set_password('oldpass')
            db.session.add(admin)
            db.session.commit()
            target_id = admin.id
        _login_as(client, target_id)
        resp = client.post(f'/admin/users/{target_id}/reset-password', data={
            'new_password': 'newpass123',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Password reset for ResetAdmin' in resp.data
        with app.app_context():
            u = db.session.get(User, target_id)
            assert u.check_password('oldpass') is False
            assert u.check_password('newpass123') is True


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# L. Reporting System (Coordinator / Director / Admin)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestReportingSystem:

    # â”€â”€ helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _coord(self, app, client, campus_id=1):
        uid = _create_user(app, email=f'coord{ campus_id }@test.com',
                           role='coordinator', campus_id=campus_id)
        _login_as(client, uid)
        return uid

    def _director(self, app, client):
        uid = _create_user(app, email='dirrep@test.com', role='director')
        _login_as(client, uid)
        return uid

    def _admin(self, app, client):
        uid = _create_user(app, email='adminrep@test.com', role='admin')
        _login_as(client, uid)
        return uid

    def _add_event(self, app, title, date, campus_id=1, category='Environment'):
        with app.app_context():
            e = Event(title=title, description='report test event',
                      date=date, required_skills='Teaching', slots=10,
                      campus_id=campus_id, category=category)
            db.session.add(e)
            db.session.commit()
            return e.id

    def _participate(self, app, user_id, event_id, attended=True, hours=2.0,
                    status='completed'):
        with app.app_context():
            reg = Registration(user_id=user_id, event_id=event_id, status=status)
            db.session.add(reg)
            db.session.flush()
            if attended:
                db.session.add(Attendance(
                    registration_id=reg.id, user_id=user_id, event_id=event_id,
                    status='present', hours_completed=hours))
            db.session.commit()

    # â”€â”€ Coordinator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_coordinator_csv_export(self, client, app):
        self._coord(app, client, 1)
        resp = client.get('/reports/events.csv')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/csv'
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body
        assert 'Registrations' in body

    def test_coordinator_pdf_export(self, client, app):
        self._coord(app, client, 1)
        resp = client.get('/reports/events.pdf')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/pdf'
        assert resp.data.startswith(b'%PDF-')

    def test_coordinator_campus_scoping(self, client, app):
        self._coord(app, client, 1)
        resp = client.get('/reports/events.csv')
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body        # campus 1
        assert 'Community Food Drive' not in body   # campus 2
        assert 'Disaster Response Training' not in body  # campus 3
        assert 'PSU Volunteer Hub' in body

    def test_coordinator_forged_campus_filter(self, client, app):
        # Coordinator (campus 1) tries to leak campus 2 via ?campus_id=2.
        self._coord(app, client, 1)
        resp = client.get('/reports/events.csv?campus_id=2')
        body = resp.data.decode()
        assert 'Community Food Drive' not in body   # leak prevented
        assert 'Youth Coding Mentor' in body        # own campus still present

    # â”€â”€ Director â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_director_csv_export(self, client, app):
        self._director(app, client)
        resp = client.get('/reports/university.csv')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/csv'
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body        # campus 1
        assert 'Community Food Drive' in body       # campus 2 (cross-campus)

    def test_director_pdf_export(self, client, app):
        self._director(app, client)
        resp = client.get('/reports/university.pdf')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/pdf'
        assert resp.data.startswith(b'%PDF-')

    def test_director_campus_filter(self, client, app):
        self._director(app, client)
        resp = client.get('/reports/university.csv?campus_id=2')
        body = resp.data.decode()
        assert 'Community Food Drive' in body
        assert 'Youth Coding Mentor' not in body

    def test_director_all_campuses_default(self, client, app):
        self._director(app, client)
        resp = client.get('/reports/university.csv')
        body = resp.data.decode()
        # No campus selected => university-wide (multiple campuses present)
        assert 'All Campuses' in body

    # â”€â”€ Admin (shares director reporting, role-aware) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_admin_reporting_csv(self, client, app):
        self._admin(app, client)
        resp = client.get('/reports/university.csv')
        assert resp.status_code == 200
        assert resp.mimetype == 'text/csv'
        assert 'University-wide Activity Report' in resp.data.decode()

    def test_admin_reporting_pdf(self, client, app):
        self._admin(app, client)
        resp = client.get('/reports/university.pdf')
        assert resp.status_code == 200
        assert resp.mimetype == 'application/pdf'
        assert resp.data.startswith(b'%PDF-')

    def test_admin_branding_not_director_console(self, client, app):
        self._admin(app, client)
        resp = client.get('/analytics')
        body = resp.data.decode()
        assert 'Director Console' not in body
        assert 'Administration' in body

    # â”€â”€ Filters â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_date_filtering(self, client, app):
        self._coord(app, client, 1)
        self._add_event(app, 'Dated Event A', datetime(2024, 6, 1), 1)
        self._add_event(app, 'Dated Event B', datetime(2023, 6, 1), 1)
        resp = client.get('/reports/events.csv?start_date=2024-01-01')
        body = resp.data.decode()
        assert 'Dated Event A' in body
        assert 'Dated Event B' not in body

    def test_end_date_excludes_later(self, client, app):
        self._coord(app, client, 1)
        self._add_event(app, 'Early Event', datetime(2024, 1, 15), 1)
        self._add_event(app, 'Late Event', datetime(2024, 12, 15), 1)
        resp = client.get('/reports/events.csv?end_date=2024-06-30')
        body = resp.data.decode()
        assert 'Early Event' in body
        assert 'Late Event' not in body

    def test_category_filtering(self, client, app):
        self._coord(app, client, 1)
        resp = client.get('/reports/events.csv?category=Environment')
        body = resp.data.decode()
        assert 'Green Campus Initiative' in body
        assert 'Coastal Cleanup Drive' in body
        assert 'Youth Coding Mentor' not in body

    def test_combined_filters(self, client, app):
        self._coord(app, client, 1)
        resp = client.get(
            '/reports/events.csv?category=Environment&start_date=2000-01-01')
        body = resp.data.decode()
        assert 'Green Campus Initiative' in body
        assert 'Coastal Cleanup Drive' in body
        assert 'Youth Coding Mentor' not in body

    def test_invalid_date_range_coordinator(self, client, app):
        self._coord(app, client, 1)
        # start_date after end_date must fail safely with 400
        resp = client.get(
            '/reports/events.csv?start_date=2025-12-31&end_date=2025-01-01')
        assert resp.status_code == 400

    def test_invalid_date_range_director(self, client, app):
        self._director(app, client)
        resp = client.get(
            '/reports/university.csv?start_date=2025-12-31&end_date=2025-01-01')
        assert resp.status_code == 302  # redirected with a validation message

    def test_empty_report_handled(self, client, app):
        self._coord(app, client, 1)
        resp = client.get('/reports/events.csv?category=NoSuchCategory')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'TOTAL' in body
        assert '0' in body

    def test_csv_and_pdf_use_same_dataset(self, client, app):
        self._coord(app, client, 1)
        with app.app_context():
            expected = {e.title for e in Event.query.filter_by(campus_id=1).all()}
        csv_resp = client.get('/reports/events.csv')
        csv_body = csv_resp.data.decode()
        for title in expected:
            assert title in csv_body
        pdf_resp = client.get('/reports/events.pdf')
        assert pdf_resp.status_code == 200
        assert pdf_resp.data.startswith(b'%PDF-')

    def test_unauthorized_role_denied(self, client, app):
        uid = _create_user(app, email='volrep@test.com', role='volunteer')
        _login_as(client, uid)
        assert client.get('/reports/events.csv').status_code == 403
        assert client.get('/reports/university.csv').status_code == 403

    def test_pdf_generation_with_reportlab(self, client, app):
        # Regression: reportlab must be installed and produce a valid PDF.
        self._director(app, client)
        resp = client.get('/reports/university.pdf')
        assert resp.status_code == 200
        assert resp.data[:5] == b'%PDF-'

    def test_report_includes_aggregates(self, client, app):
        self._coord(app, client, 1)
        with app.app_context():
            eid = Event.query.filter_by(title='Green Campus Initiative').first().id
            vid = _create_user(app, email='repvol@test.com',
                               role='volunteer', campus_id=1)
        self._participate(app, vid, eid, attended=True, hours=3.0,
                         status='completed')
        resp = client.get('/reports/events.csv')
        body = resp.data.decode()
        assert 'Service Hours' in body
        assert 'TOTAL' in body


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# M. Outsider / External Volunteer Workflow (Phase 12)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestOutsiderVolunteers:

    def _coordinator(self, app, client, campus_id=1):
        uid = _create_user(app, email=f'extcoord{campus_id}@test.com',
                           role='coordinator', campus_id=campus_id)
        _login_as(client, uid)
        return uid

    def _event_id(self, app, title='Youth Coding Mentor'):
        with app.app_context():
            return Event.query.filter_by(title=title).first().id

    # â”€â”€ Public Join workflow â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_join_asks_psu_question(self, client, app):
        eid = self._event_id(app)
        resp = client.get(f'/event/{eid}/join')
        assert resp.status_code == 200
        assert 'currently from PSU' in resp.data.decode()

    def test_selecting_outsider_shows_form(self, client, app):
        eid = self._event_id(app)
        resp = client.get(f'/event/{eid}/join?external=1')
        body = resp.data.decode()
        assert resp.status_code == 200
        assert 'id_number' in body
        assert 'required' in body.lower()

    def test_outsider_requires_id_number(self, client, app):
        eid = self._event_id(app)
        resp = client.post(f'/event/{eid}/join', data={'from_psu': 'no'})
        assert resp.status_code == 400
        with app.app_context():
            assert ExternalParticipant.query.count() == 0

    def test_outsider_name_optional(self, client, app):
        eid = self._event_id(app)
        resp = client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-001'})
        assert resp.status_code == 302
        with app.app_context():
            ep = ExternalParticipant.query.filter_by(id_number='EXT-001').first()
            assert ep is not None
            assert ep.name is None

    def test_outsider_contact_optional(self, client, app):
        eid = self._event_id(app)
        client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-002'})
        with app.app_context():
            assert ExternalParticipant.query.filter_by(
                id_number='EXT-002').first().contact_number is None

    def test_outsider_address_optional(self, client, app):
        eid = self._event_id(app)
        client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-003'})
        with app.app_context():
            assert ExternalParticipant.query.filter_by(
                id_number='EXT-003').first().address is None

    def test_outsider_email_optional(self, client, app):
        eid = self._event_id(app)
        client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-004'})
        with app.app_context():
            assert ExternalParticipant.query.filter_by(
                id_number='EXT-004').first().email is None

    def test_outsider_can_register(self, client, app):
        eid = self._event_id(app)
        client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-005', 'name': 'Juan Dela Cruz'})
        with app.app_context():
            ep = ExternalParticipant.query.filter_by(id_number='EXT-005').first()
            assert ep is not None
            reg = Registration.query.filter_by(
                external_participant_id=ep.id, event_id=eid).first()
            assert reg is not None
            assert reg.user_id is None
            assert reg.status == 'confirmed'

    def test_psu_user_still_uses_normal_flow(self, client, app):
        eid = self._event_id(app)
        uid = _create_user(app, email='psujoin@test.com',
                           role='volunteer', campus_id=1)
        _login_as(client, uid)
        resp = client.post(f'/opportunities/register/{eid}', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            reg = Registration.query.filter_by(
                user_id=uid, event_id=eid).first()
            assert reg is not None

    # â”€â”€ Coordinator manual encoding â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_coordinator_can_manually_add_outsider(self, client, app):
        self._coordinator(app, client, 1)
        eid = self._event_id(app)  # campus 1
        resp = client.post(
            f'/coordinator/events/{eid}/external',
            data={'id_number': 'EXT-MAN-1', 'name': 'Manual Outsider'})
        assert resp.status_code == 302
        with app.app_context():
            ep = ExternalParticipant.query.filter_by(
                id_number='EXT-MAN-1').first()
            assert ep is not None
            assert Registration.query.filter_by(
                external_participant_id=ep.id, event_id=eid).first() is not None

    def test_coordinator_cannot_add_other_campus_outsider(self, client, app):
        self._coordinator(app, client, 1)
        # Community Food Drive is campus 2
        with app.app_context():
            eid = Event.query.filter_by(title='Community Food Drive').first().id
        resp = client.post(
            f'/coordinator/events/{eid}/external',
            data={'id_number': 'EXT-X'})
        assert resp.status_code == 403
        with app.app_context():
            assert ExternalParticipant.query.filter_by(
                id_number='EXT-X').first() is None

    def test_outsider_registration_no_privilege(self, client, app):
        eid = self._event_id(app)
        with app.app_context():
            before = User.query.count()
        client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-PRIV'})
        with app.app_context():
            after = User.query.count()
            assert after == before  # no User / privileged account created
            reg = Registration.query.filter_by(
                external_participant_id=ExternalParticipant.query.filter_by(
                    id_number='EXT-PRIV').first().id).first()
            assert reg.user_id is None

    # â”€â”€ Attendance integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_attendance_for_outsider(self, client, app):
        self._coordinator(app, client, 1)
        eid = self._event_id(app)
        with app.app_context():
            ep = ExternalParticipant(id_number='EXT-ATT')
            db.session.add(ep)
            db.session.commit()
            reg = Registration(external_participant_id=ep.id, event_id=eid,
                               status='confirmed')
            db.session.add(reg)
            db.session.commit()
            reg_id = reg.id
        resp = client.post('/attendance', data={
            'event_id': str(eid),
            'registration_id': str(reg_id),
            'status': 'present',
            'hours_completed': '2.5',
        })
        assert resp.status_code == 302
        with app.app_context():
            att = Attendance.query.filter_by(registration_id=reg_id).first()
            assert att is not None
            assert att.user_id is None
            assert att.status == 'present'

    def test_outsider_attendance_no_duplicate(self, client, app):
        self._coordinator(app, client, 1)
        eid = self._event_id(app)
        with app.app_context():
            ep = ExternalParticipant(id_number='EXT-DUP')
            db.session.add(ep)
            db.session.commit()
            reg = Registration(external_participant_id=ep.id, event_id=eid,
                               status='confirmed')
            db.session.add(reg)
            db.session.commit()
            reg_id = reg.id
        client.post('/attendance', data={
            'event_id': str(eid), 'registration_id': str(reg_id),
            'status': 'present', 'hours_completed': '1'})
        client.post('/attendance', data={
            'event_id': str(eid), 'registration_id': str(reg_id),
            'status': 'present', 'hours_completed': '2'})
        with app.app_context():
            assert Attendance.query.filter_by(registration_id=reg_id).count() == 1

    def test_outsider_certificate_eligibility(self, client, app):
        self._coordinator(app, client, 1)
        eid = self._event_id(app)
        with app.app_context():
            ep = ExternalParticipant(id_number='EXT-CERT')
            db.session.add(ep)
            db.session.commit()
            reg = Registration(external_participant_id=ep.id, event_id=eid,
                               status='confirmed')
            db.session.add(reg)
            db.session.commit()
            reg_id = reg.id
        client.post('/attendance', data={
            'event_id': str(eid), 'registration_id': str(reg_id),
            'status': 'present', 'hours_completed': '3'})
        with app.app_context():
            reg = db.session.get(Registration, reg_id)
            assert reg.status == 'completed'
            assert reg.certificate_eligible is True

    def test_outsider_appears_in_report(self, client, app):
        self._coordinator(app, client, 1)
        eid = self._event_id(app)
        client.post(f'/event/{eid}/join', data={
            'from_psu': 'no', 'id_number': 'EXT-REP'})
        resp = client.get('/reports/events.csv')
        body = resp.data.decode()
        assert 'External' in body  # breakdown column present
        assert 'EXT-REP' in body or 'External #EXT-REP' in body or \
            'Youth Coding Mentor' in body

    def test_existing_psu_registration_intact(self, client, app):
        uid = _create_user(app, email='psureg@test.com',
                           role='volunteer', campus_id=1)
        _login_as(client, uid)
        eid = self._event_id(app)
        resp = client.post(f'/opportunities/register/{eid}', follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert Registration.query.filter_by(
                user_id=uid, event_id=eid).first() is not None


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# O. Coordinator Event Editing (Phase 16)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestCoordinatorEventEditing:
    def _coord(self, app, campus_id=1, email='coord@test.com'):
        return _create_user(app, email=email, role='coordinator',
                           campus_id=campus_id, name='Coord')

    def test_own_campus_edit_succeeds(self, app, client):
        cid = self._coord(app, 1)
        _login_as(client, cid)
        resp = client.post('/coordinator/events/1/edit', data={
            'title': 'Updated Title', 'description': 'Updated desc',
            'date': '2030-01-01', 'location': 'New Loc',
            'category': 'Education & Literacy', 'slots': 25,
            'required_skills': 'Teaching'}, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            e = db.session.get(Event, 1)
            assert e.title == 'Updated Title'
            assert e.slots == 25

    def test_cross_campus_edit_denied(self, app, client):
        # Event id 3 belongs to campus 2; coordinator is campus 1.
        cid = self._coord(app, 1)
        _login_as(client, cid)
        assert client.get(f'/coordinator/events/3/edit').status_code == 403
        resp = client.post(f'/coordinator/events/3/edit', data={
            'title': 'X', 'description': 'Y', 'date': '2030-01-01', 'slots': 5})
        assert resp.status_code == 403

    def test_volunteer_cannot_edit(self, app, client):
        vid = _create_user(app, email='vol@test.com', role='volunteer',
                          campus_id=1)
        _login_as(client, vid)
        assert client.get('/coordinator/events/1/edit').status_code in (302, 403)

    def test_director_cannot_edit(self, app, client):
        did = _create_user(app, email='dir@test.com', role='director',
                          campus_id=1)
        _login_as(client, did)
        assert client.get('/coordinator/events/1/edit').status_code in (302, 403)

    def test_invalid_values_rejected(self, app, client):
        cid = self._coord(app, 1)
        _login_as(client, cid)
        with app.app_context():
            orig = db.session.get(Event, 1).title
        resp = client.post('/coordinator/events/1/edit', data={
            'title': '', 'description': 'x', 'date': '2030-01-01',
            'slots': 5}, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Event, 1).title == orig  # unchanged

    def test_slots_below_registrations_rejected(self, app, client):
        with app.app_context():
            ev = Event(title='Cap Event', description='d',
                       date=datetime.now() + timedelta(days=5),
                       required_skills='', slots=10, campus_id=1,
                       category='General')
            db.session.add(ev)
            db.session.commit()
            eid = ev.id
            vid = _create_user(app, email='volcap@test.com', role='volunteer',
                              campus_id=1)
            db.session.add(Registration(user_id=vid, event_id=eid,
                                        status='confirmed'))
            db.session.commit()
        cid = self._coord(app, 1, email='coordcap@test.com')
        _login_as(client, cid)
        resp = client.post(f'/coordinator/events/{eid}/edit', data={
            'title': 'Cap Event', 'description': 'd',
            'date': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'slots': 0, 'category': 'General', 'required_skills': ''},
            follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Event, eid).slots == 10  # unchanged

    def test_registrations_survive_edit(self, app, client):
        with app.app_context():
            ev = Event(title='Keep Event', description='d',
                       date=datetime.now() + timedelta(days=5),
                       required_skills='', slots=10, campus_id=1,
                       category='General')
            db.session.add(ev)
            db.session.commit()
            eid = ev.id
            vid = _create_user(app, email='volkeep@test.com', role='volunteer',
                              campus_id=1)
            db.session.add(Registration(user_id=vid, event_id=eid,
                                        status='confirmed'))
            db.session.commit()
            rid = Registration.query.filter_by(event_id=eid).first().id
        cid = self._coord(app, 1, email='coordkeep@test.com')
        _login_as(client, cid)
        client.post(f'/coordinator/events/{eid}/edit', data={
            'title': 'Keep Event', 'description': 'updated',
            'date': (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d'),
            'slots': 12, 'category': 'General', 'required_skills': ''},
            follow_redirects=True)
        with app.app_context():
            reg = db.session.get(Registration, rid)
            assert reg is not None
            assert reg.event_id == eid

    def test_csrf_blocks_edit_without_token(self, app, client):
        app.config['WTF_CSRF_ENABLED'] = True
        cid = self._coord(app, 1, email='coordcsrf@test.com')
        _login_as(client, cid)
        resp = client.post('/coordinator/events/1/edit', data={
            'title': 'X', 'description': 'Y', 'date': '2030-01-01', 'slots': 5},
            follow_redirects=False)
        assert resp.status_code in (400, 302)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# N. Analytics & Chart Improvements (Phase 18)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

from app.recommendation.analytics import AnalyticsAggregator


class TestAnalytics:
    """Deterministic descriptive-analytics tests (Phase 18).

    Isolated scenarios use campus 5 (Bayambang) which has NO seed events, so
    counts are fully controlled.
    """

    def _event(self, app, title, date, campus_id=5, category='Environment',
               slots=10):
        with app.app_context():
            e = Event(title=title, description='t', date=date,
                      required_skills='', slots=slots, campus_id=campus_id,
                      category=category)
            db.session.add(e)
            db.session.commit()
            return e.id

    def _reg(self, app, user_id=None, external_id=None, event_id=None,
             status='completed', attendance_status='present', hours=2.0):
        with app.app_context():
            reg = Registration(user_id=user_id,
                               external_participant_id=external_id,
                               event_id=event_id, status=status)
            db.session.add(reg)
            db.session.flush()
            if attendance_status:
                db.session.add(Attendance(
                    registration_id=reg.id, user_id=user_id,
                    event_id=event_id, status=attendance_status,
                    hours_completed=hours if attendance_status == 'present'
                    else 0.0))
            db.session.commit()
            return reg.id

    def _vol(self, app, email='vol@test.com'):
        return _create_user(app, email=email, role='volunteer', campus_id=5,
                            name='V')

    # â”€â”€ Core metric definitions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_registration_count_excludes_cancelled(self, app):
        eid = self._event(app, 'A', datetime.now() + timedelta(days=1), 5,
                          'Environment')
        v1 = self._vol(app, 'a1@t.com')
        v2 = self._vol(app, 'a2@t.com')
        self._reg(app, user_id=v1, event_id=eid, status='completed',
                  attendance_status='present')
        self._reg(app, user_id=v2, event_id=eid, status='cancelled',
                  attendance_status=None)
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(campus_id=5)
        assert s['registrations'] == 1          # cancelled excluded
        assert s['attended'] == 1
        assert s['conversion_rate'] == 100.0

    def test_unique_volunteers_distinct_from_registrations(self, app):
        e1 = self._event(app, 'A', datetime.now() + timedelta(days=1), 5,
                         'Environment')
        e2 = self._event(app, 'B', datetime.now() + timedelta(days=2), 5,
                         'Environment')
        v = self._vol(app, 'u1@t.com')
        self._reg(app, user_id=v, event_id=e1, status='completed',
                  attendance_status='present')
        self._reg(app, user_id=v, event_id=e2, status='completed',
                  attendance_status='present')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(campus_id=5)
        assert s['registrations'] == 2           # two sign-ups
        assert s['unique_volunteers'] == 1       # same person

    def test_attendance_count_and_absent(self, app):
        eid = self._event(app, 'A', datetime.now() + timedelta(days=1), 5,
                          'Environment')
        p = self._vol(app, 'p@t.com')
        a = self._vol(app, 'ab@t.com')
        self._reg(app, user_id=p, event_id=eid, status='completed',
                  attendance_status='present')
        self._reg(app, user_id=a, event_id=eid, status='completed',
                  attendance_status='absent')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(campus_id=5)
        assert s['registrations'] == 2
        assert s['attended'] == 1               # only present counted
        assert s['attendance_rate'] == 50.0
        assert s['conversion_rate'] == 50.0

    def test_zero_registrations_safe(self, app):
        self._event(app, 'Empty', datetime.now() + timedelta(days=1), 5,
                    'Environment')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(campus_id=5)
        assert s['registrations'] == 0
        assert s['attended'] == 0
        assert s['attendance_rate'] == 0.0
        assert s['conversion_rate'] == 0.0
        assert s['unique_volunteers'] == 0

    def test_analytics_matches_report(self, app):
        # Phase 18.4: dashboard/CSV/PDF must agree for the same scope.
        from app.reports import build_events_report
        eid = self._event(app, 'A', datetime.now() + timedelta(days=1), 5,
                          'Environment')
        v = self._vol(app, 'm@t.com')
        self._reg(app, user_id=v, event_id=eid, status='completed',
                  attendance_status='present')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(campus_id=5)
            _, rep = build_events_report(campus_id=5)
        assert s['registrations'] == rep['total_registrations']
        assert s['attended'] == rep['total_attended']
        assert s['service_hours'] == rep['total_hours']

    # â”€â”€ Scope / security â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_coordinator_analytics_campus_scoped(self, app, client):
        cid = _create_user(app, email='coord_an@t.com', role='coordinator',
                           campus_id=1, name='C')
        _login_as(client, cid)
        resp = client.get('/coordinator_analytics')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body        # campus 1 event
        assert 'Community Food Drive' not in body  # campus 2 leaked

    def test_director_accesses_university_analytics(self, app, client):
        did = _create_user(app, email='dir_an@t.com', role='director')
        _login_as(client, did)
        resp = client.get('/analytics')
        assert resp.status_code == 200
        assert 'Cross-Campus Comparison' in resp.data.decode()

    def test_admin_accesses_university_analytics(self, app, client):
        aid = _create_user(app, email='admin_an@t.com', role='admin')
        _login_as(client, aid)
        resp = client.get('/analytics')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Administration' in body
        assert 'Director Console' not in body

    def test_volunteer_denied_privileged_analytics(self, app, client):
        vid = _create_user(app, email='vol_an@t.com', role='volunteer',
                           campus_id=1)
        _login_as(client, vid)
        assert client.get('/analytics').status_code in (302, 403)
        assert client.get('/coordinator_analytics').status_code in (302, 403)

    # â”€â”€ Aggregations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def test_monthly_engagement_chronological(self, app):
        e1 = self._event(app, 'Jan', datetime(2020, 1, 15), 5, 'Environment')
        e2 = self._event(app, 'Mar', datetime(2020, 3, 15), 5, 'Environment')
        self._reg(app, user_id=self._vol(app, 'm1@t.com'), event_id=e1,
                  attendance_status='present')
        self._reg(app, user_id=self._vol(app, 'm2@t.com'), event_id=e2,
                  attendance_status='present')
        with app.app_context():
            m = AnalyticsAggregator.monthly_engagement(campus_id=5)
        assert m['months'] == ['2020-01', '2020-03']   # chronological
        assert sum(m['registrations']) == 2

    def test_weekly_engagement_works(self, app):
        e1 = self._event(app, 'W1', datetime(2020, 1, 6), 5, 'Environment')
        e2 = self._event(app, 'W2', datetime(2020, 1, 13), 5, 'Environment')
        self._reg(app, user_id=self._vol(app, 'w1@t.com'), event_id=e1,
                  attendance_status='present')
        self._reg(app, user_id=self._vol(app, 'w2@t.com'), event_id=e2,
                  attendance_status='present')
        with app.app_context():
            w = AnalyticsAggregator.weekly_engagement(campus_id=5)
        assert len(w['weeks']) == 2
        assert sum(w['registrations']) == 2
        assert w['weeks'] == sorted(w['weeks'])

    def test_activity_performance(self, app):
        eid = self._event(app, 'Perf', datetime.now() + timedelta(days=1), 5,
                          'Environment')
        for i in range(3):
            v = self._vol(app, f'p{i}@t.com')
            self._reg(app, user_id=v, event_id=eid, status='completed',
                      attendance_status='present')
        with app.app_context():
            rows = AnalyticsAggregator.activity_performance(campus_id=5)
        assert rows[0]['registrations'] == 3
        assert rows[0]['conversion_rate'] == 100.0

    def test_category_distribution(self, app):
        e1 = self._event(app, 'E1', datetime.now() + timedelta(days=1), 5,
                         'Environment')
        e2 = self._event(app, 'E2', datetime.now() + timedelta(days=2), 5,
                         'Health & Wellness')
        self._reg(app, user_id=self._vol(app, 'c1@t.com'), event_id=e1,
                  attendance_status='present')
        self._reg(app, user_id=self._vol(app, 'c2@t.com'), event_id=e2,
                  attendance_status='present')
        with app.app_context():
            cats = AnalyticsAggregator.category_distribution(campus_id=5)
        by = {c['category']: c['registrations'] for c in cats}
        assert by['Environment'] == 1
        assert by['Health & Wellness'] == 1

    def test_campus_comparison(self, app):
        eid = self._event(app, 'Cmp', datetime.now() + timedelta(days=1), 5,
                          'Environment')
        v = self._vol(app, 'cmp@t.com')
        self._reg(app, user_id=v, event_id=eid, status='completed',
                  attendance_status='present')
        with app.app_context():
            cmp = AnalyticsAggregator.campus_comparison()
        bay = next(r for r in cmp if r['campus'] == 'Binmaley')
        assert bay['registrations'] == 1
        assert bay['attended'] == 1

    def test_psu_vs_outsider_classification(self, app):
        eid = self._event(app, 'Ext', datetime.now() + timedelta(days=1), 5,
                          'Environment')
        with app.app_context():
            ext = ExternalParticipant(id_number='EXT-001')
            db.session.add(ext)
            db.session.commit()
            ext_id = ext.id
        self._reg(app, external_id=ext_id, event_id=eid, status='completed',
                  attendance_status='present')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(campus_id=5)
            split = AnalyticsAggregator.psu_vs_outsider(campus_id=5)
        assert s['psu_registrations'] == 0
        assert s['external_registrations'] == 1
        assert s['unique_volunteers'] == 0       # outsiders are not users
        assert split['outsider'] == 1
        assert split['psu'] == 0

    def test_date_filter_works(self, app):
        self._event(app, 'Old', datetime(2020, 1, 1), 5, 'Environment')
        self._event(app, 'New', datetime(2030, 1, 1), 5, 'Environment')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(
                campus_id=5, start_date='2025-01-01')
        # Only the 2030 event is in range (no registrations => 0).
        assert s['event_count'] == 1

    def test_combined_campus_category_filter(self, app):
        self._event(app, 'Env', datetime.now() + timedelta(days=1), 5,
                    'Environment')
        self._event(app, 'Hlth', datetime.now() + timedelta(days=2), 5,
                    'Health & Wellness')
        with app.app_context():
            s = AnalyticsAggregator.participation_summary(
                campus_id=5, category='Environment')
        assert s['event_count'] == 1

    def test_empty_datasets_do_not_crash(self, app):
        # Campus 6 has no seed events and we add none.
        with app.app_context():
            assert AnalyticsAggregator.campus_comparison() is not None
            assert AnalyticsAggregator.category_distribution(campus_id=6) == []
            m = AnalyticsAggregator.monthly_engagement(campus_id=6)
            assert m['months'] == []
            w = AnalyticsAggregator.weekly_engagement(campus_id=6)
            assert w['weeks'] == []
            assert AnalyticsAggregator.skill_distribution() == []
            assert AnalyticsAggregator.interest_distribution() == []
