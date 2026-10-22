"""Idle-session boundaries, isolated data, and browser-script regressions."""
from pathlib import Path
import re
import shutil
import subprocess
import time

import pytest

from tests.test_app import app, client, _create_user, _login_as
from app.models import db
from app.models.user import User
from app.models.policy import TermsRevision
from app.services.session_idle import IDLE_MESSAGE


@pytest.fixture
def clock(monkeypatch):
    now = [time.time()]
    monkeypatch.setattr('app.services.session_idle.time.time', lambda: now[0])
    return now


def sign_in(app, client, clock, role='volunteer'):
    uid = _create_user(app, role=role)
    _login_as(client, uid)
    with client.session_transaction() as session:
        session['last_activity_at'] = clock[0]
    return uid


def test_defaults_and_real_login_session_cookie(app, client, clock):
    _create_user(app)
    response = client.post('/auth/login', data={
        'identifier': 'test@example.com', 'password': 'password123', 'remember': 'on'})
    assert response.status_code == 302
    assert app.config['SESSION_IDLE_TIMEOUT_SECONDS'] == 1800
    assert app.config['SESSION_IDLE_WARNING_SECONDS'] == 60
    cookies = response.headers.getlist('Set-Cookie')
    assert not any('remember_token=' in cookie for cookie in cookies)
    session_cookie = next(c for c in cookies if c.startswith('session='))
    assert 'Expires=' not in session_cookie and 'Max-Age=' not in session_cookie
    with client.session_transaction() as session:
        assert session['last_activity_at'] == clock[0]
        assert session.get('_permanent') is not True


@pytest.mark.parametrize('role', ['volunteer', 'coordinator', 'director', 'admin'])
def test_exact_timeout_all_roles_clears_auth_and_explains(app, client, clock, role):
    sign_in(app, client, clock, role)
    clock[0] += 1800
    response = client.get('/dashboard')
    assert response.status_code == 302 and response.location.endswith('/auth/login')
    assert response.headers['Cache-Control'] == 'no-store'
    with client.session_transaction() as session:
        assert '_user_id' not in session and 'last_activity_at' not in session
    with app.app_context():
        assert IDLE_MESSAGE.encode() in client.get('/auth/login').data


def test_request_before_expiry_renews_and_head_static_do_not(app, client, clock):
    sign_in(app, client, clock)
    original = clock[0]
    clock[0] += 1799
    assert client.head('/auth/session').status_code == 200
    assert client.get('/static/scripts/session-idle.js').status_code == 200
    with client.session_transaction() as session:
        assert session['last_activity_at'] == original
    assert client.get('/dashboard').status_code == 302
    with client.session_transaction() as session:
        assert session['last_activity_at'] == clock[0]


def test_status_reads_do_not_renew_but_post_does(app, client, clock):
    sign_in(app, client, clock)
    original = clock[0]
    clock[0] += 1740
    response = client.get('/auth/session')
    assert response.status_code == 200
    assert response.json['expires_at'] == original + 1800
    assert response.json['warning_seconds'] == 60
    assert response.headers['Cache-Control'] == 'no-store'
    clock[0] += 59
    response = client.post('/auth/session')
    assert response.json['expires_at'] == clock[0] + 1800
    clock[0] += 1800
    assert client.post('/auth/session').status_code == 401
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_expired_post_cannot_mutate_and_status_cannot_revive(app, client, clock):
    uid = sign_in(app, client, clock)
    app.add_url_rule('/idle-write-probe', 'idle_write_probe',
                     lambda: setattr(db.session.get(User, uid), 'name', 'Changed'), methods=['POST'])
    clock[0] += 1800
    assert client.post('/idle-write-probe').status_code == 302
    assert db.session.get(User, uid).name == 'Test User'
    with app.app_context():
        assert client.get('/auth/session').status_code == 401


@pytest.mark.parametrize('last', ['invalid', float('nan'), float('inf'), True, 'future'])
def test_bad_timestamps_fail_closed(app, client, clock, last):
    sign_in(app, client, clock)
    with client.session_transaction() as session:
        session['last_activity_at'] = clock[0] + 1 if last == 'future' else last
    assert client.get('/auth/session').status_code == 401


def test_legacy_cookie_initialized_once_then_times_out(app, client, clock):
    _login_as(client, _create_user(app))
    assert client.get('/auth/session').json['expires_at'] == clock[0] + 1800
    clock[0] += 1800
    assert client.get('/auth/session').status_code == 401


def test_csrf_required_for_renewal(app, client, clock):
    sign_in(app, client, clock)
    app.config['WTF_CSRF_ENABLED'] = True
    body = client.get('/help').get_data(as_text=True)
    token = re.search(r'data-csrf-token="([^"]+)"', body)[1]
    with client.session_transaction() as session:
        original = session['last_activity_at']
    clock[0] += 10
    assert client.post('/auth/session').status_code == 400
    with client.session_transaction() as session:
        assert session['last_activity_at'] == original
    assert client.post('/auth/session', headers={'X-CSRFToken': token}).status_code == 200


def test_active_session_renews_csrf_token_without_weakening_protection(app, client, clock):
    sign_in(app, client, clock)
    app.config['WTF_CSRF_ENABLED'] = True
    token = client.get('/auth/session').json['csrf_token']
    original = token
    for _ in range(4):
        clock[0] += 1000
        # Match real HTTP requests rather than retaining the fixture's g.csrf_token.
        with app.app_context():
            response = client.post('/auth/session', headers={'X-CSRFToken': token})
        assert response.status_code == 200
        token = response.json['csrf_token']
    assert client.post('/auth/session', headers={'X-CSRFToken': original}).status_code == 400
    assert client.post('/auth/session', headers={'X-CSRFToken': token}).status_code == 200


def test_password_reset_invalidation_not_bypassed_by_session_endpoint(app, client, clock):
    uid = sign_in(app, client, clock)
    db.session.get(User, uid).auth_version += 1
    db.session.commit()
    assert client.post('/auth/session').status_code == 401
    with app.app_context():
        assert b'password was changed' in client.get('/auth/login').data


def test_policy_gates_still_apply_but_allow_session_checks(app, client, clock):
    sign_in(app, client, clock)
    db.session.add(TermsRevision(version='idle-qa', title='Idle QA', body='Synthetic QA', is_active=True))
    db.session.commit()
    assert client.get('/dashboard').location.endswith('/auth/terms')
    assert client.get('/auth/session').status_code == 200
    body = client.get('/auth/terms').data
    assert b'id="session-idle"' in body
    clock[0] += 1800
    assert client.post('/auth/terms', data={'accept_terms': 'on'}).location.endswith('/auth/login')


def test_shared_layouts_only_show_warning_when_authenticated(app, client, clock):
    for path in ['/auth/login', '/help']:
        assert b'id="session-idle"' not in client.get(path).data
    sign_in(app, client, clock)
    for path in ['/help', '/volunteer_dash']:
        # The shared fixture holds an app context; reset Flask-Login's g cache.
        with app.app_context():
            response = client.get(path)
        assert response.status_code == 200
        assert b'id="session-idle"' in response.data
        assert response.headers['Cache-Control'] == 'no-store'


def test_session_script_behaviors():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is required for JavaScript checks')
    result = subprocess.run([node, '--test', str(Path(__file__).with_name('session-idle.test.cjs'))],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
