"""Recommendations must be explainable, live, scoped, and safe to send."""
import json
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy.exc import SQLAlchemyError
from flask import g

from app.annual_goals import goal_guidance
from app.dashboard import operational_guidance, present_guidance, scheduling_scope
from app.models import db
from app.models.event import Event
from app.models.notification import Notification
from app.models.user import User
from tests.test_annual_goals import app, client, target, _create_user, _login_as
from tests.test_dashboard_decisions import decisions
from tests.html_helpers import parse_html


def post_data(code='remaining_goals', **changes):
    return dict(follow_up_campus_id='1', goal_year=str(date.today().year),
                guidance_kind=code, report_scope=json.dumps({'period': ['all']}), **changes)


def test_live_rules_priorities_exact_counts_and_completion(app, decisions):
    from app.reports import build_events_report
    rows, _ = build_events_report(campus_id=1)
    tips = operational_guidance(rows, 'All Dates')
    assert [tip['code'] for tip in tips] == ['pending_attendance', 'missed_targets', 'low_attendance']
    assert '1 missing attendance' in tips[0]['evidence']
    assert '1 awaiting completion' in tips[0]['evidence']
    assert tips[2]['evidence'].startswith('1 activities')
    assert [tip['code'] for tip in operational_guidance(rows, 'All Dates', show_targets=False)] == ['pending_attendance', 'low_attendance']
    row = next(row for row in rows if row['title'] == 'Exactly seventy five')
    assert operational_guidance([row], 'All Dates') == []
    row['outcome_attended'] = 299999
    row['registrations'] = 400000
    row['target_participants'] = 0
    assert operational_guidance([row], 'All Dates')[0]['code'] == 'low_attendance'
    row['attendance_complete'] = False
    assert [tip['code'] for tip in operational_guidance([row], 'All Dates')] == ['pending_attendance']
    row['ended'] = False
    assert operational_guidance([row], 'All Dates') == []


@pytest.mark.parametrize('total,met,expected', [(0, 0, 'no_targets'), (2, 0, 'remaining_goals'), (2, 2, None)])
def test_annual_rules(total, met, expected):
    tips = goal_guidance(dict(total=total, met=met, pending=0, year=2026))
    assert [tip['code'] for tip in tips] == ([expected] if expected else [])
    assert not any('overdue' in tip['text'] for tip in tips)


@pytest.mark.parametrize('filter_key', ['category', 'sex', 'sdg_id', 'activity_name', 'attention', 'event_id', 'department', 'status'])
def test_filtered_empty_is_not_no_activities(filter_key):
    assert not scheduling_scope({filter_key: 'selected'})
    assert operational_guidance([], 'Filtered Scope') == []
    assert operational_guidance([], 'All Dates', allow_scheduling=True)[0]['code'] == 'no_activities'


def test_primary_plus_two_and_goal_actions(app, client, decisions):
    from app.reports import build_events_report
    director_id = _create_user(app, role='director', campus_id=1)
    _login_as(client, director_id)
    rows, _ = build_events_report(campus_id=1)
    with app.test_request_context('/director_dash'):
        g._login_user = db.session.get(User, director_id)
        records = operational_guidance(rows, 'All Dates') + goal_guidance(dict(total=0, met=0, pending=0, year=2026))
        tips = present_guidance(records, 1, 2026)
        assert [tip['priority'] for tip in tips] == [1, 2, 3]
        assert tips[1]['url'].endswith('/annual-goals/workspace')


def test_reminder_delivery_identity_links_and_scope_state(app, client):
    coordinator = _create_user(app, role='coordinator', campus_id=1)
    other = _create_user(app, email='second@test.com', role='coordinator', campus_id=1)
    inactive = _create_user(app, email='inactive@test.com', role='coordinator', campus_id=1)
    db.session.get(User, inactive)._is_active = False
    db.session.commit()
    director = _create_user(app, email='director@test.com', role='director')
    target(campus=1, actual=0)
    _login_as(client, director)
    data = post_data(calendar_year='2026', calendar_month='12', award_year='2025', category='Environment')
    response = client.post('/director/campus-follow-up', data=data)
    query = parse_qs(urlsplit(response.location).query)
    assert query['calendar_month'] == ['12'] and query['category'] == ['Environment']
    assert query['guidance_open'] == ['1'] and urlsplit(response.location).fragment == 'campus-guidance'
    assert Notification.query.filter_by(notification_type='campus_guidance').count() == 2
    assert Notification.query.filter_by(user_id=inactive).count() == 0
    note = Notification.query.filter_by(user_id=coordinator).one()
    payload = json.loads(note.message)
    assert '0.0%' in payload['text'] and '0 of 1' in payload['text']
    client.post('/director/campus-follow-up', data=data)
    assert Notification.query.filter_by(notification_type='campus_guidance').count() == 2
    _login_as(client, coordinator)
    page = parse_html(client.get('/notifications').get_data(as_text=True))
    link = next(link for link in page.all('a') if 'Review Campus Records' in link.text)
    assert parse_qs(urlsplit(link.attrs['href']).query)['campus'] == ['1']
    assert client.get(link.attrs['href']).status_code == 200
    assert '"identity"' not in page.text


def test_cleared_and_missing_coordinator_reminders(app, client):
    director = _create_user(app, role='director')
    _login_as(client, director)
    target(campus=1, actual=4)
    response = client.post('/director/campus-follow-up', data=post_data(), follow_redirects=True)
    assert 'recommendation has cleared' in response.get_data(as_text=True)
    response = client.post('/director/campus-follow-up', data=post_data('no_targets', **{}))
    assert Notification.query.count() == 0
    response = client.post('/director/campus-follow-up', data=dict(post_data('no_targets'), follow_up_campus_id='2'), follow_redirects=True)
    assert 'No active coordinator is assigned' in response.get_data(as_text=True)


@pytest.mark.parametrize('role', ['coordinator', 'admin', 'volunteer'])
def test_reminder_is_director_only(app, client, role):
    _login_as(client, _create_user(app, role=role, campus_id=1))
    assert client.post('/director/campus-follow-up', data=post_data()).status_code == 403
    assert Notification.query.count() == 0


def test_forged_scope_event_and_csrf_rejected(app, client, decisions):
    _login_as(client, _create_user(app, role='director'))
    for changes in [dict(report_scope='[]'), dict(guidance_kind='unknown'),
                    dict(guidance_event_id='invalid'), dict(report_scope='{"redirect":["https://example.com"]}'),
                    dict(guidance_kind='no_activities', guidance_event_id=str(decisions['Other campus outcome']))]:
        assert client.post('/director/campus-follow-up', data=dict(post_data(), **changes)).status_code == 400
    response = client.post('/director/campus-follow-up', data=post_data('pending_attendance',
        guidance_event_id=str(decisions['Other campus outcome'])))
    assert response.status_code == 302 and Notification.query.count() == 0
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/director/campus-follow-up', data=post_data()).status_code == 400


def test_operational_reminder_and_resolved_condition(app, client, decisions):
    coordinator = _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, _create_user(app, email='director@test.com', role='director'))
    activity = decisions['Recorded low attendance']
    data = post_data('missed_targets', guidance_event_id=str(activity))
    assert client.post('/director/campus-follow-up', data=data).status_code == 302
    note = Notification.query.filter_by(user_id=coordinator).one()
    assert note.related_event_id == activity
    assert '1 attended / 3 participant target' in json.loads(note.message)['text']
    db.session.get(Event, activity).target_participants = 1
    db.session.commit()
    page = client.post('/director/campus-follow-up', data=data, follow_redirects=True).get_data(as_text=True)
    assert 'recommendation has cleared' in page and Notification.query.count() == 1
    _login_as(client, coordinator)
    page = parse_html(client.get('/notifications').get_data(as_text=True))
    link = next(link for link in page.all('a') if 'Review Campus Records' in link.text)
    assert parse_qs(urlsplit(link.attrs['href']).query)['event_id'] == [str(activity)]


def test_notification_legacy_and_malformed_content(app, client):
    uid = _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, uid)
    db.session.add_all([Notification(user_id=uid, title='Legacy Notice', message='Legacy plain text.'),
        Notification(user_id=uid, title='Broken Notice', message='[]', notification_type='campus_guidance')])
    db.session.commit()
    body = client.get('/notifications').get_data(as_text=True)
    assert 'Legacy plain text.' in body and 'guidance message is unavailable' in body


def test_coordinator_lookup_is_batched(app, client):
    _login_as(client, _create_user(app, role='director'))
    queries = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        if 'users.campus_id' in statement and "users.role" in statement:
            queries.append(statement)
    sa_event.listen(db.engine, 'before_cursor_execute', capture)
    try:
        assert client.get('/director_dash').status_code == 200
    finally:
        sa_event.remove(db.engine, 'before_cursor_execute', capture)
    assert len([sql for sql in queries if 'DISTINCT users.campus_id' in sql]) == 1


def test_delivery_failure_rolls_back(app, client, monkeypatch):
    _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, _create_user(app, email='director@test.com', role='director'))
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'commit', lambda: (_ for _ in ()).throw(SQLAlchemyError('test failure')))
        response = client.post('/director/campus-follow-up', data=post_data('no_targets'))
    assert response.status_code == 302 and Notification.query.count() == 0
