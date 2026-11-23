"""The director ranking shares campus goal definitions and uses exact ratios."""
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest

from app.annual_goals import campus_ranking, dashboard_context, sample_rows
from app.models.notification import Notification
from datetime import date
from tests.test_annual_goals import app, client, target, _login_as, _create_user


def campus(name, met, total, campus_id=1, pending=0):
    return dict(campus=name, campus_id=campus_id, met=met, total=total, pending=pending,
                rate=round(met/total*100,1) if total else None)


def test_single_leader_counts_pending_and_excludes_no_targets():
    ranked = campus_ranking([campus('Pending campus',1,4,1,pending=3),
                             campus('Leader',2,3,2),campus('No targets',0,0,3)])
    assert ranked['state'] == 'ranked'
    assert [item['campus'] for item in ranked['leaders']] == ['Leader']
    assert len(ranked['rows']) == 2 and ranked['rows'][1]['pending'] == 3


def test_exact_ties_with_different_denominators_are_retained():
    ranked = campus_ranking([campus('Zulu',1,2,1),campus('Alpha',2,4,2),campus('Other',1,3,3)])
    assert [item['campus'] for item in ranked['leaders']] == ['Alpha','Zulu']


def test_rounding_does_not_create_false_ties():
    first, second = campus('Rounded lower',2,3,1), campus('Rounded higher',667,1000,2)
    assert first['rate'] == second['rate'] == 66.7
    assert campus_ranking([first,second])['leaders'] == [second]


@pytest.mark.parametrize('rows,state', [([], 'unavailable'),([campus('None',0,0)],'unavailable'),
    ([campus('Pending',0,4,pending=4),campus('Unmet',0,2,2)],'zero')])
def test_empty_and_zero_states_do_not_name_a_winner(rows,state):
    result = campus_ranking(rows)
    assert result['state'] == state and result['leaders'] == []


def test_director_routes_exclude_history_without_sex_queries(app,client,monkeypatch):
    from tests.test_ui_reimagining import screen
    target(campus=1,actual=4,shared='campus-shared')
    target(campus=2)
    uid = _create_user(app,email='campus-ranking-director@test.com',role='director',campus_id=1)
    _login_as(client,uid)
    forbidden = Mock(side_effect=AssertionError('Director overview must not calculate sex participation'))
    monkeypatch.setattr('app.annual_goals.participation',forbidden)
    response,data=screen(client,app,'/workspace/overview')
    assert response.status_code == 200 and data['campus_rollup']['total'] == 0
    assert client.get('/annual-goals?history=1&campus=1').status_code == 200
    forbidden.assert_not_called()


def test_sample_year_and_drilldowns_preserved(app,monkeypatch):
    comparisons = Mock(return_value=[dict(campus('Sample campus',3,4,2), rows=sample_rows(2))])
    monkeypatch.setattr('app.annual_goals.comparisons',comparisons)
    with app.test_request_context('/director_dash?goal_year=2024&sample=1'):
        plan = dashboard_context(2026)
    comparisons.assert_called_once_with(2024,True)
    assert plan['sample'] and plan['year'] == 2024
    assert parse_qs(urlsplit(plan['campus_ranking']['rows'][0]['detail_url']).query) == {
        'year':['2024'],'campus':['2'],'sample':['1']}


def test_campus_rollup_keeps_historical_evidence_separate(app, client):
    from tests.test_ui_reimagining import screen
    target(campus=1,actual=4,shared='both')
    target(campus=1,actual=4,shared='both')
    target(campus=2)
    target(actual=4)
    _login_as(client,_create_user(app,role='director',email='rollup@test.com'))
    response,data=screen(client,app,'/workspace/overview')
    assert response.status_code == 200
    assert data['campus_rollup']['total'] == data['goals']['total'] == 0
    assert data['campus_rollup']['plans'] == {'AOP':{'total':0,'met':0}}
    from tests.test_annual_goals import summary
    assert summary(campus_id=1)['met'] == 1 and summary()['met'] == 1


def test_coordinator_participation_and_director_empty_states(app,client):
    from tests.test_ui_reimagining import screen
    uid=_create_user(app,email='campus-ranking-coordinator@test.com',role='coordinator',campus_id=1)
    _login_as(client,uid)
    response,data=screen(client,app,'/workspace/overview')
    assert response.status_code == 200
    assert data['goals']['campus_id'] == 1
    from app.annual_goals import participation
    assert participation(date.today().year,1)['total'] >= 0
    uid=_create_user(app,email='campus-ranking-empty@test.com',role='director',campus_id=1)
    _login_as(client,uid)
    assert 'No AOP Goals' in client.get('/annual-goals').get_data(as_text=True)
    preview=client.get('/annual-goals?sample=1',follow_redirects=True)
    assert preview.status_code == 200 and b'Sample Data' in preview.data


def test_director_can_notify_active_campus_coordinator(app, client):
    from tests.test_aop_commitments import publish, submit
    coordinator=_create_user(app,email='follow-up-coordinator@test.com',role='coordinator',campus_id=1)
    director=_create_user(app,email='follow-up-director@test.com',role='director',campus_id=1)
    _login_as(client,director)
    goal=publish(client)
    _login_as(client,coordinator)
    submit(client,goal,'4')
    _login_as(client,director)
    response=client.post('/director/campus-follow-up',data={
        'follow_up_campus_id':'1','goal_year':'2026'})
    assert response.status_code == 302
    note=Notification.query.filter_by(user_id=coordinator,notification_type='campus_guidance').one()
    assert 'Lingayen' in note.title and '0 of 1' in note.message
