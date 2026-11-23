"""Director hierarchy and grouped queue navigation preserve underlying facts."""
from urllib.parse import parse_qs,urlsplit
from datetime import timedelta
import pytest
from app.models import db
from app.models.event import Event,Registration,Attendance
from app.services.activity_workflow import local_now
from app.services.staff_overview import FINDING_LABELS
from tests.test_workspace_overhaul import app,client,actors,sign_in
from tests.test_ui_reimagining import screen
from tests.test_annual_goals import target
from tests.html_helpers import parse_html,form_values,form_with_control


def test_director_headlines_reuse_values_and_preserve_secondary_statistics(client,app,actors):
    target(campus=1,actual=4,shared='shared');target(campus=1,actual=4,shared='shared',kind='ASP')
    target(campus=2);target(actual=4)
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview?period=all')
    page=parse_html(response.text)
    tiles=page.all('article',**{'class':'metric-tile'})
    assert [t.one('span',**{'class':'metric-title'}).text for t in tiles]==[
        'Conducted Activities','Verified Attendees','Campus Annual Achievement','Findings to Review']
    assert [t.all('strong')[0].text for t in tiles]==[str(data['conducted']),str(data['attendees']),'1 / 2',str(data['finding_total'])]
    assert data['campus_rollup']['pending']==1 and data['goals']['total']==1
    secondary=page.one('section',**{'class':'director-secondary-summary'})
    assert 'Approved Activities' in secondary.text and 'Volunteer Accounts' in secondary.text
    assert 'All time' in secondary.text and str(data['accounts']) in secondary.text
    primary=response.text.split('class="director-primary-grid"')[1].split('class="director-secondary-summary"')[0]
    assert 'Campus Accomplishments' in primary and 'Needs Attention' in primary
    assert 'id="annual-title"' not in primary and 'data-month-chart' not in primary and 'data-sex-chart' not in primary


@pytest.mark.parametrize('role,path',[('coordinator','/workspace/overview'),('director','/workspace/reports/results')])
def test_other_metric_consumers_keep_five_tiles(client,actors,role,path):
    sign_in(client,actors,role)
    page=parse_html(client.get(path).text)
    assert len(page.all('article',**{'class':'metric-tile'}))==5
    assert not page.all('section',**{'class':'director-secondary-summary'})


def test_overview_scope_controls_and_links_keep_context(client,actors):
    sign_in(client,actors,'director')
    query='?period=quarterly&segment=2&year=2025&campus_id=1&sex=female'
    page=parse_html(client.get('/workspace/overview'+query).text)
    values=form_values(form_with_control(page,'period'))
    assert values['year']==['2025'] and values['segment']==['2'] and values['campus_id']==['1'] and values['sex']==['female']
    link=next(a for a in page.all('a') if a.text=='Open Report')
    assert parse_qs(urlsplit(link.attrs['href']).query)['sex']==['female']
    assert any(a.attrs.get('href')=='#annual-title' for a in page.all('a'))


@pytest.mark.parametrize('value',['invented','pending','<script>'])
def test_invalid_finding_type_rejected(client,actors,value):
    sign_in(client,actors,'director')
    assert client.get('/workspace/follow-up',query_string={'finding_type':value}).status_code==400


def test_repeated_finding_type_rejected(client,actors):
    sign_in(client,actors,'director')
    assert client.get('/workspace/follow-up?finding_type=no_targets&finding_type=no_targets').status_code==400


def test_finding_groups_link_to_matching_scoped_queue(client,app,actors):
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview?period=all&campus_id=1')
    page=parse_html(response.text)
    from app.services.finding_reviews import GROUPS
    links=[a for a in page.all('a') if 'review_group=' in a.attrs.get('href','')]
    assert len(links)==4
    for link,group in zip(links,data['attention_summary']['groups']):
        query=parse_qs(urlsplit(link.attrs['href']).query)
        assert query['review_group']==[group['key']] and query['campus_id']==['1'] and query['page']==['1']
        queued,context=screen(client,app,link.attrs['href'])
        assert context['total']==group['total']
        assert all(item['code'] in GROUPS[group['key']][1] and item['campus'].id==1 for item in context['items'])
        reset=next(a for a in parse_html(queued.text).all('a') if a.text=='Clear Review Filters')
        reset_args=parse_qs(urlsplit(reset.attrs['href']).query)
        assert 'review_group' not in reset_args and reset_args['campus_id']==['1']


def test_queue_filters_before_pagination_and_does_not_change_facts(client,app,actors):
    now=local_now()
    for i in range(28):
        event=Event(title=f'Queue fixture {i}',description='Synthetic fixture',date=now-timedelta(days=2),
            end_date=now-timedelta(days=1),campus_id=1,lifecycle_status='approved')
        db.session.add(event);db.session.flush()
        db.session.add(Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed'))
    db.session.commit()
    before=(Event.query.count(),Registration.query.count(),Attendance.query.count())
    sign_in(client,actors,'director')
    url='/workspace/follow-up?period=all&activity_name=Queue+fixture&finding_type=pending_attendance'
    _,first=screen(client,app,url)
    response,second=screen(client,app,url+'&page=2')
    assert first['total']==second['total']==28 and len(first['items'])==25 and len(second['items'])==3
    previous=next(a for a in parse_html(response.text).all('a') if a.text=='Previous')
    assert parse_qs(urlsplit(previous.attrs['href']).query)['finding_type']==['pending_attendance']
    assert before==(Event.query.count(),Registration.query.count(),Attendance.query.count())
    sign_in(client,actors,'other')
    _,other=screen(client,app,url)
    assert other['total']==0


def test_known_empty_finding_type_and_unset_annual_state(client,actors):
    sign_in(client,actors,'director')
    response=client.get('/workspace/follow-up?period=all&finding_type=record_attendance&activity_name=NoMatch')
    assert response.status_code==200 and 'No follow-up findings' in response.text
    page=parse_html(client.get('/workspace/overview?year=1900').text)
    third=page.all('article',**{'class':'metric-tile'})[2]
    assert third.all('strong')[0].text=='Not Set'
    assert 'Active Reviews' not in page.text and 'Reviewed and Closed' not in page.text


def test_valid_finding_types_stay_within_coordinator_scope(client,app,actors):
    sign_in(client,actors)
    for code in FINDING_LABELS:
        _,data=screen(client,app,'/workspace/follow-up?campus_id=2&finding_type='+code)
        assert data['campus_id']==1 and all(item['code']==code for item in data['items'])


def test_preview_limits_groups_without_losing_total(client,app,actors,monkeypatch):
    from app.models.event import Campus
    import app.services.workspace_reports as reports
    campus=db.session.get(Campus,1)
    findings=[dict(code=code,campus=campus,scope='Synthetic scope') for code in FINDING_LABELS]
    monkeypatch.setattr(reports,'follow_up_items',lambda data:findings)
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview')
    page=parse_html(response.text)
    assert data['finding_total']==8
    links=[a for a in page.all('a') if 'review_group=' in a.attrs.get('href','')]
    assert len(links)==4 and sum(g['total'] for g in data['attention_summary']['groups'])==8
    assert [parse_qs(urlsplit(a.attrs['href']).query)['review_group'][0] for a in links]==[g['key'] for g in data['attention_summary']['groups']]
