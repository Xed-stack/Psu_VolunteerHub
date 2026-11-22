"""Campus controls move without changing report or annual calculation scope."""
from urllib.parse import parse_qs, urlsplit

import pytest
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html, form_values, form_with_control
from tests.test_verified_sex_reports import evidence


def test_dashboard_compare_link_resets_only_campus_scope(client,actors):
    sign_in(client,actors,'director')
    origin='/workspace/overview?year=2025&period=quarterly&segment=2&campus_id=1&campus=1&campus=2&campus_mode=exclude&sex=female&category=Environment&page=3'
    page=parse_html(client.get(origin).text)
    section=next(s for s in page.all('section') if s.attrs.get('data-tour-id')=='campus-comparison')
    assert section.one('h2').text=='Campus Accomplishments'
    link=next(a for a in section.all('a') if a.text=='Compare Campuses')
    destination=urlsplit(link.attrs['href']);args=parse_qs(destination.query)
    assert destination.path=='/workspace/reports/results' and destination.fragment=='campus-comparison'
    assert not {'campus','campus_id','campus_mode','page'} & args.keys()
    assert args['view']==['summary'] and args['return_to']==[origin]
    assert args['year']==['2025'] and args['segment']==['2'] and args['period']==['quarterly']
    assert args['sex']==['female'] and args['category']==['Environment']
    assert client.get(link.attrs['href']).status_code==200


@pytest.mark.parametrize('view',['summary','activities','participation'])
def test_comparison_controls_and_top_form_preserve_scope(client,actors,view):
    sign_in(client,actors,'director')
    path='/workspace/reports/results?period=all&campus=1&campus=2&campus_mode=exclude&sex=female&view='+view
    page=parse_html(client.get(path).text)
    top=form_with_control(page,'period',tags=('select',))
    values=form_values(top)
    assert top.all('select',name='campus_id')
    assert values['campus']==['1','2'] and values['campus_mode']==['exclude']
    assert all(i.attrs.get('type')=='hidden' for i in top.all('input',name='campus'))
    assert not top.all('select',name='campus_mode')
    if view=='summary':
        section=page.one('section',id='campus-comparison')
        assert section.one('h2').text=='Campus Comparison'
        form=form_with_control(section,'campus_mode')
        assert urlsplit(form.attrs['action']).fragment=='campus-comparison'
        assert len(form.all('input',name='campus'))==9
        assert [c.text for c in form.all('label') if c.all('input',name='campus')]==sorted(c.text for c in form.all('label') if c.all('input',name='campus'))
        submitted=form_values(form)
        assert submitted['sex']==['female'] and submitted['period']==['all']
        assert submitted['campus']==['1','2'] and submitted['page']==['1'] and submitted['view']==['summary']
        assert client.get(form.attrs['action'],query_string=[(k,v) for k,vs in submitted.items() for v in vs]).status_code==200
    else:
        link=next(a for a in page.all('a') if a.text=='Adjust Campus Comparison')
        assert urlsplit(link.attrs['href']).fragment=='campus-comparison'
        assert parse_qs(urlsplit(link.attrs['href']).query)['campus']==['1','2']


def test_comparison_keeps_primary_restriction_and_reset_preserves_other_filters(client,app,actors,evidence):
    sign_in(client,actors,'director')
    path='/workspace/reports/results?period=all&campus_id=1&campus=1&campus=2&campus_mode=include&sex=female'
    response,data=screen(client,app,path)
    assert data['sex_breakdown']['total']==3 and data['campus_id']==1
    page=parse_html(response.text);form=form_with_control(page.one('section',id='campus-comparison'),'campus_mode')
    assert 'Primary Campus: Lingayen' in form.text
    assert form_values(form)['campus_id']==['1']
    reset=next(a for a in form.all('a') if a.text=='Reset Comparison')
    query=parse_qs(urlsplit(reset.attrs['href']).query)
    assert not {'campus','campus_mode'} & query.keys()
    assert query['sex']==['female'] and query['campus_id']==['1'] and query['period']==['all']
    assert urlsplit(reset.attrs['href']).fragment=='campus-comparison'


@pytest.mark.parametrize('mode,expected',[('include',9),('exclude',1)])
def test_comparison_filters_whole_report_and_exports(client,app,actors,evidence,mode,expected):
    sign_in(client,actors,'director')
    query='?period=all&activity_name=Breakdown&campus=1&campus_mode='+mode
    _,data=screen(client,app,'/workspace/reports/results'+query)
    assert data['attendees']==data['sex_breakdown']['total']==expected
    import csv,io
    rows=list(csv.DictReader(io.StringIO(client.get('/workspace/reports/export/csv'+query).data.decode('utf-8-sig'))))
    assert sum(sum(int(r['Verified Attendance: '+label]) for label in ['Female','Male','Prefer Not to Say','Not Recorded']) for r in rows)==expected


def test_coordinator_and_other_chart_consumers_keep_existing_scope(client,actors):
    sign_in(client,actors)
    page=parse_html(client.get('/workspace/reports/results?period=all&campus=2').text)
    assert page.one('section',id='campus-comparison').one('h2').text=='Campus Comparison'
    assert not page.all('select',name='campus_mode') and not page.all('select',name='campus_id')
    assert len(page.all('span',**{'class':'sex-chart-key sex-chart-key--unrecorded'}))==1
    sign_in(client,actors,'director')
    text=client.get('/workspace/campuses/1?period=all').text
    assert any(h.text=='Campus Accomplishments' for h in parse_html(text).all('h2'))
    assert 'comparison-filters' not in text
