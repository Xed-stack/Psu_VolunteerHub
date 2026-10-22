"""Registration decisions and cancellation use disposable SQLite data."""
from datetime import datetime, timedelta
from html import unescape
import re
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy.exc import IntegrityError

from tests.test_app import app, client, _create_user, _login_as
from app.models import db
from app.models.event import Event, Registration, Attendance, CancellationRequest
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.routes.events import _cancellation_state


@pytest.fixture
def record(app, client):
    uid = _create_user(app, campus_id=1)
    _login_as(client, uid)
    registration = Registration(user_id=uid, event_id=1, status='confirmed')
    db.session.add(registration)
    db.session.commit()
    return registration


@pytest.mark.parametrize('status', ['pending', 'confirmed', 'completed', 'cancelled'])
@pytest.mark.parametrize('attendance', [None, 'present', 'absent', 'excused'])
def test_dashboard_and_route_share_status_attendance_rules(app, client, record, status, attendance):
    record.status = status
    if attendance:
        db.session.add(Attendance(registration_id=record.id, event_id=1,
                                  user_id=record.user_id, status=attendance))
    db.session.commit()
    allowed = status in ('pending', 'confirmed') and attendance is None
    body = client.get('/volunteer_dash').get_data(as_text=True)
    assert ('>Request cancellation</a>' in body) == allowed
    response = client.get(f'/registrations/{record.id}/cancel')
    assert response.status_code == (200 if allowed else 302)
    response = client.post(f'/registrations/{record.id}/cancel', data={'reason': 'Academic Conflict'})
    assert response.status_code == 302
    assert CancellationRequest.query.count() == int(allowed)


@pytest.mark.parametrize('saved_deadline', [False, True])
@pytest.mark.parametrize('offset, allowed', [(-1, False), (0, False), (1, True)])
def test_effective_deadline_exact_boundary(record, saved_deadline, offset, allowed):
    now = datetime(2030, 1, 1, 10)
    deadline = now + timedelta(seconds=offset)
    record.event.date = now + timedelta(days=2) if saved_deadline else deadline
    record.event.cancellation_deadline = deadline if saved_deadline else None
    state = _cancellation_state(record, now)
    assert state['can_request'] == allowed and state['deadline'] == deadline


@pytest.mark.parametrize('decision', ['pending', 'approved', 'rejected'])
@pytest.mark.parametrize('method', ['get', 'post'])
def test_existing_request_is_retained_and_cannot_be_repeated(client, record, decision, method):
    cancellation = CancellationRequest(registration_id=record.id, reason='Other',
        details='<script>private reason</script>', status=decision,
        review_note='<b>private coordinator note</b>' if decision != 'pending' else None,
        reviewed_at=datetime.utcnow() if decision != 'pending' else None)
    db.session.add(cancellation)
    db.session.commit()
    before = (cancellation.id, cancellation.status, cancellation.details, cancellation.review_note)
    response = getattr(client, method)(f'/registrations/{record.id}/cancel', data={'reason': 'Academic Conflict'})
    assert response.status_code == 302
    assert CancellationRequest.query.count() == 1
    assert before == (cancellation.id, cancellation.status, cancellation.details, cancellation.review_note)
    body = client.get('/volunteer_dash').get_data(as_text=True)
    assert '>Request cancellation</a>' not in body
    assert '&lt;script&gt;private reason&lt;/script&gt;' in body
    assert '<script>private reason</script>' not in body
    if decision == 'approved':
        assert 'Previous cancellation decision' in body and 'you joined again' in body
    elif decision == 'pending':
        assert 'Your registration remains active until approval' in body
    else:
        assert 'Rejected' in body and '&lt;b&gt;private coordinator note&lt;/b&gt;' in body


def test_validation_retains_values_and_conditional_details(client, record):
    endpoint = f'/registrations/{record.id}/cancel'
    response = client.post(endpoint, data={'reason': 'bogus', 'details': '<long> retained'})
    body = response.get_data(as_text=True)
    assert response.status_code == 400 and 'reason-error' in body
    assert '&lt;long&gt; retained' in body and 'aria-invalid="true"' in body
    response = client.post(endpoint, data={'reason': 'Other', 'details': '  '})
    body = response.get_data(as_text=True)
    assert response.status_code == 400 and 'details-error' in body
    assert re.search(r'value="Other" required checked', body)
    # Without scripts, changing to a non-Other reason must not trap the user.
    assert 'required' not in re.search(r'<textarea[^>]+>', body)[0]
    assert CancellationRequest.query.count() == 0
    assert client.post(endpoint, data={'reason': 'Academic Conflict'}).status_code == 302
    assert CancellationRequest.query.one().details is None


def test_context_prg_duplicate_audit_and_notification_once(app, client, record):
    coordinator = _create_user(app, email='coord-ui@example.test', role='coordinator', campus_id=1)
    _create_user(app, email='other-coord-ui@example.test', role='coordinator', campus_id=2)
    query = 'status=confirmed&campus=1&category=Education&start_date=2026-01-01&end_date=2031-01-01&show=10&calendar_year=2030&calendar_month=2&next=//bad.example&return_to=https://bad.example'
    endpoint = f'/registrations/{record.id}/cancel?{query}'
    body = client.get(endpoint).get_data(as_text=True)
    back = unescape(re.search(r'href="([^"]+)"[^>]*>Back to My registrations', body)[1])
    args = parse_qs(urlsplit(back).query)
    assert urlsplit(back).fragment == f'registration-{record.id}'
    assert 'next' not in args and 'return_to' not in args and args['show'] == ['10']
    response = client.post(endpoint, data={'reason': 'Other', 'details': 'Synthetic test request'})
    assert response.location == back
    assert record.status == 'confirmed'
    for _ in range(2):
        client.get(response.location)
        client.post(endpoint, data={'reason': 'Other', 'details': 'Do not replace'})
    assert CancellationRequest.query.count() == 1
    assert AuditLog.query.filter_by(action='cancellation_requested').count() == 1
    notes = Notification.query.filter_by(notification_type='cancellation_requested').all()
    assert len(notes) == 1 and notes[0].user_id == coordinator


def test_stale_deadline_and_expired_session_do_not_create_request(client, record):
    endpoint = f'/registrations/{record.id}/cancel'
    assert client.get(endpoint).status_code == 200
    record.event.cancellation_deadline = datetime.now() - timedelta(seconds=1)
    db.session.commit()
    assert client.post(endpoint, data={'reason': 'Other', 'details': 'Stale'}).status_code == 302
    assert CancellationRequest.query.count() == 0
    record.event.cancellation_deadline = None
    db.session.commit()
    with client.session_transaction() as session:
        session['last_activity_at'] = time.time() - 1801
    assert '/auth/login' in client.post(endpoint, data={'reason': 'Academic Conflict'}).location
    assert CancellationRequest.query.count() == 0


def test_owner_only_and_csrf(app, client, record):
    endpoint = f'/registrations/{record.id}/cancel'
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post(endpoint, data={'reason': 'Academic Conflict'}).status_code == 400
    body = client.get(endpoint).get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', body)[1]
    assert client.post(endpoint, data={'reason': 'Academic Conflict', 'csrf_token': token}).status_code == 302
    assert CancellationRequest.query.count() == 1
    other = _create_user(app, email='unrelated-ui@example.test', campus_id=1)
    with app.app_context():
        stranger = app.test_client()
        _login_as(stranger, other)
        assert stranger.get(endpoint).status_code == 403
        assert 'Request and decision details' not in stranger.get('/volunteer_dash').get_data(as_text=True)
    with app.app_context():
        anonymous = app.test_client()
        assert '/auth/login' in anonymous.get(endpoint).location
    assert client.get('/registrations/999999/cancel').status_code == 404


@pytest.mark.parametrize('role', ['coordinator', 'director', 'admin'])
def test_other_roles_cannot_access_cancellation(app, record, role):
    uid = _create_user(app, email=f'{role}-registration@example.test', role=role, campus_id=1)
    with app.app_context():
        other = app.test_client()
        _login_as(other, uid)
        assert other.get(f'/registrations/{record.id}/cancel').status_code == 403
        assert other.post(f'/registrations/{record.id}/cancel').status_code == 403


def test_empty_and_linked_registration_records(app, client, record):
    body = client.get('/volunteer_dash').get_data(as_text=True)
    assert f'/opportunities/{record.event_id}' in body and 'Cancellation deadline' in body
    assert '(activity start)' in body
    assert 'No registrations match these filters' in client.get('/volunteer_dash?status=cancelled').get_data(as_text=True)
    db.session.delete(record)
    db.session.commit()
    assert 'No registrations yet' in client.get('/volunteer_dash').get_data(as_text=True)


def test_unique_conflict_returns_existing_request_without_duplicate_notifications(client, record, monkeypatch):
    # Model the losing request observing a committed winner after rollback.
    original_flush = db.session.flush
    original_rollback = db.session.rollback
    def conflict(*args, **kwargs):
        raise IntegrityError('insert cancellation', {}, Exception('duplicate registration'))
    def rollback_with_winner():
        original_rollback()
        monkeypatch.setattr(db.session, 'flush', original_flush)
        db.session.add(CancellationRequest(registration_id=record.id, reason='Other', details='Winner'))
        db.session.commit()
    monkeypatch.setattr(db.session, 'flush', conflict)
    monkeypatch.setattr(db.session, 'rollback', rollback_with_winner)
    response = client.post(f'/registrations/{record.id}/cancel', data={'reason': 'Academic Conflict'})
    assert response.status_code == 302
    assert CancellationRequest.query.one().details == 'Winner'
    assert Notification.query.count() == 0 and AuditLog.query.count() == 0
