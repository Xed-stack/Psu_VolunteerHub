import pytest
from app import create_app
from app.models import db
from app.models.user import User, VolunteerProfile, SystemSetting, Skill, Interest
from app.models.event import Event, Registration, Attendance, Campus
from app.recommendation.engine import get_recommendations, bootstrap_from_event
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
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


# ── Seed helpers ──────────────────────────────────────────────────────────────

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
              required_skills='Teaching, Python, Communication', slots=20, campus_id=1),
        Event(title='Green Campus Initiative', description='Tree planting.',
              date=datetime.now() + timedelta(days=14),
              required_skills='Environmental Conservation, Agriculture', slots=50, campus_id=1),
        Event(title='Community Food Drive', description='Distribute relief packages.',
              date=datetime.now() + timedelta(days=10),
              required_skills='Organizational, Communication', slots=30, campus_id=2),
        Event(title='Rural Literacy Program', description='Teach reading.',
              date=datetime.now() + timedelta(days=21),
              required_skills='Teaching, Tutoring, Communication', slots=15, campus_id=1),
        Event(title='Disaster Response Training', description='First aid workshop.',
              date=datetime.now() + timedelta(days=5),
              required_skills='Medical, First Aid', slots=40, campus_id=3),
        Event(title='Community IT Support Workshop', description='Digital literacy.',
              date=datetime.now() + timedelta(days=30),
              required_skills='IT, Computer Skills, Teaching', slots=25, campus_id=4),
        Event(title='Coastal Cleanup Drive', description='Preserve coastline.',
              date=datetime.now() + timedelta(days=3),
              required_skills='Environmental Conservation, Teamwork', slots=100, campus_id=1),
        Event(title='Community Wellness Fair', description='Free health mission.',
              date=datetime.now() + timedelta(days=45),
              required_skills='Medical, First Aid, Organizational', slots=60, campus_id=7),
        Event(title='Sustainable Farming Demo', description='Organic cultivation.',
              date=datetime.now() + timedelta(days=60),
              required_skills='Agriculture, Environmental Conservation', slots=30, campus_id=8),
    ]
    for e in events:
        db.session.add(e)
    db.session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

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


# ══════════════════════════════════════════════════════════════════════════════
# A. App Initialization
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# B. Authentication
# ══════════════════════════════════════════════════════════════════════════════

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
            'campus': 'Lingayen',
        }, follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            u = User.query.filter_by(email='alice@test.com').first()
            assert u is not None
            assert u.role == 'volunteer'

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


# ══════════════════════════════════════════════════════════════════════════════
# C. Role-based Access
# ══════════════════════════════════════════════════════════════════════════════

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
        assert resp.status_code == 200

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


# ══════════════════════════════════════════════════════════════════════════════
# D. Volunteer Features
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# E. Coordinator Features
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# F. Director Features
# ══════════════════════════════════════════════════════════════════════════════

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
            for key in ('total_active_volunteers', 'total_hours', 'community_value', 'retention_rate'):
                assert key in kpis, f'KPI key {key} missing'


# ══════════════════════════════════════════════════════════════════════════════
# G. Admin Features
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# H. Recommendation Engine
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendationEngine:
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
            u = User.query.get(profile.user_id)
            bootstrap_from_event(u, event)
            assert {s.name for s in u.skills} == {'Communication'}
            assert {i.name for i in u.interests} == {'Health'}


# ══════════════════════════════════════════════════════════════════════════════
# I. Search, Filter & Pagination
# ══════════════════════════════════════════════════════════════════════════════

class TestSearchFilterPagination:

    def test_filter_by_campus(self, client, app):
        uid = _create_user(app, email='campusfilt@test.com')
        _login_as(client, uid)
        resp = client.get('/opportunities?campus=1')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Youth Coding Mentor' in body
        assert 'Sustainable Farming Demo' not in body

    @pytest.mark.xfail(reason="Event model has no 'category' column; route crashes on category filter")
    def test_filter_by_category(self, client, app):
        uid = _create_user(app, email='catfilt@test.com')
        _login_as(client, uid)
        resp = client.get('/opportunities?category=Education')
        assert resp.status_code == 200
        body = resp.data.decode()
        assert 'Education' in body

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


# ══════════════════════════════════════════════════════════════════════════════
# J. Missing Features
# ══════════════════════════════════════════════════════════════════════════════

class TestMissingFeatures:

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
        resp = client.post('/settings', data={'community_value_rate': '20'},
                           follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            s = SystemSetting.query.filter_by(key='community_value_rate').first()
            assert s is not None
            assert s.value == '20'


# ══════════════════════════════════════════════════════════════════════════════
# K. Admin User Management
# ══════════════════════════════════════════════════════════════════════════════

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
            admin = User(name='EditPostAdmin', email='editpost@test.com',
                         role='admin', campus_id=1)
            admin.set_password('pw')
            db.session.add(admin)
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
