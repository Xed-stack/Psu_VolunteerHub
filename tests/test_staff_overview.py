"""Staff layouts must preserve scopes and repair the campus annual rollup."""
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from app.models import db
from app.models.event import Event
from app.services.activity_workflow import local_now
from app.services.staff_overview import overview_context
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_ui_reimagining import screen
from tests.test_annual_goals import target
from tests.test_system_performance import query_count
from tests.html_helpers import parse_html, form_with_control, form_values


def test_rollup_separates_university_targets_and_merges_within_campus(client,app,actors):
    target(campus=1,actual=4,shared='both')
    target(campus=1,actual=4,shared='both',kind='ASP')
    target(campus=2,actual=0)
    target(campus=2)
    target(actual=4)
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview')
    assert (data['campus_rollup']['met'],data['campus_rollup']['total'],data['campus_rollup']['pending']) == (1,3,1)
    assert data['campus_rollup']['rate'] == 33.3
    assert data['campus_rollup']['plans'] == {'AOP':{'met':1,'total':3},'ASP':{'met':1,'total':1}}
    assert data['goals']['total'] == data['goals']['met'] == 1
    assert b'Campus Annual Achievement' in response.data and b'University-Wide Targets' in response.data
    with query_count(app) as queries:
        overview_context(data,data['follow_ups'])
    assert len(queries) == 0
    _,filtered=screen(client,app,'/workspace/overview?category=No+such+category')
    assert filtered['conducted'] == 0 and filtered['campus_rollup']['total'] == 3


def test_scoped_rollup_unknowns_and_scope_controls_preserve_filters(client,app,actors):
    target(campus=1,actual=4)
    target(campus=2)
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview?period=all&campus=1&campus=2&campus_mode=include&activity_name=100%25_&sex=female&page=3')
    assert data['campus_rollup']['total'] == 2 and data['campus_rollup']['pending'] == 1
    assert len(data['campus_comparison']) == 2
    page=parse_html(response.get_data(as_text=True))
    values=form_values(form_with_control(page,'period'))
    assert values['campus'] == ['1','2']
    assert values['activity_name'] == ['100%_'] and values['sex'] == ['female']
    assert 'page' not in values and 'tour' not in values
    values['year']=[str(local_now().year)]
    assert client.get('/workspace/overview',query_string=[(k,v) for k,vs in values.items() for v in vs]).status_code == 200
    link=next(a for a in page.all('a') if 'Advanced Filters' in a.text)
    query=parse_qs(urlsplit(link.attrs['href']).query)
    assert query['campus'] == ['1','2'] and query['sex'] == ['female']
    _,empty=screen(client,app,'/workspace/overview?campus_id=3')
    assert empty['campus_rollup']['rate'] is None


def test_agenda_is_five_chronological_campus_events_and_keeps_ongoing_action(client,app,actors):
    now=local_now()
    for row in Event.query.all():
        row.date=now-timedelta(days=10);row.end_date=now-timedelta(days=9)
    for i in range(7):
        start=now+timedelta(days=i) if i else now-timedelta(hours=1)
        db.session.add(Event(title=f'Agenda {i}',description='Fixture',date=start,
            end_date=start+timedelta(hours=3),campus_id=1,slots=20,lifecycle_status='approved'))
    db.session.add(Event(title='Wrong campus agenda',description='Fixture',date=now+timedelta(hours=1),
        end_date=now+timedelta(hours=2),campus_id=2,slots=20,lifecycle_status='approved'))
    db.session.commit()
    sign_in(client,actors)
    response,data=screen(client,app,'/workspace/overview?campus_id=2&category=No+match')
    assert [e.title for e in data['agenda']] == [f'Agenda {i}' for i in range(5)]
    assert data['campus_id'] == 1 and len(data['campus_comparison']) == 1
    assert b'Record Attendance' in response.data and b'Wrong campus agenda' not in response.data
    assert b'/attendance?' in response.data and b'/coordinator/calendar' in response.data


def test_grouped_preview_keeps_full_queue_individual_actions(client,app,actors):
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview')
    assert sum(group['count'] for group in data['finding_groups']) == len(data['follow_ups'])
    assert len([group for group in data['finding_groups'] if group['code']=='no_targets']) == 1
    assert b'Notify Coordinator' not in response.data
    queue=client.get('/workspace/follow-up')
    assert queue.status_code == 200 and b'Notify Coordinator' in queue.data


def test_campus_drilldown_returns_to_filtered_overview(client,app,actors):
    sign_in(client,actors,'director')
    path='/workspace/overview?period=all&category=Environment'
    response=client.get(path)
    page=parse_html(response.get_data(as_text=True))
    detail=next(a.attrs['href'] for a in page.all('a') if a.attrs.get('href','').startswith('/workspace/campuses/'))
    detail_page=parse_html(client.get(detail).get_data(as_text=True))
    assert any(a.attrs.get('href') == path for a in detail_page.all('a'))


def test_overview_populated_annual_query_count_does_not_grow_per_target(client,app,actors):
    target(campus=1,actual=4)
    sign_in(client,actors,'director')
    with query_count(app) as first:
        assert client.get('/workspace/overview').status_code == 200
    for i in range(12):
        target(campus=1 if i%2 else 2,actual=4)
    db.session.expire_all()
    with query_count(app) as many:
        assert client.get('/workspace/overview').status_code == 200
    assert len(many) <= len(first)+2, (len(first),len(many))
