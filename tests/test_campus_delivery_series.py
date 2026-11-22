"""Campus delivery series reconcile with full-scope totals and form submissions."""
from datetime import datetime
import pytest
from werkzeug.datastructures import MultiDict
from app.models import db
from app.models.event import Event
from app.models.user import User
from app.services.workspace_reports import workspace_report
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app,client,actors,sign_in
from tests.test_ui_reimagining import screen
from tests.test_system_performance import query_count
from tests.html_helpers import parse_html,form_values,form_with_control


@pytest.fixture
def deliveries(actors):
    def add(campus,month=1,year=2025,**changes):
        values=dict(title='Line fixture',description='Synthetic delivery',campus_id=campus,
            date=datetime(year,month,10,9),end_date=datetime(year,month,10,12),lifecycle_status='approved',category='Environment')
        values.update(changes)
        event=Event(**values);db.session.add(event);return event
    add(1);add(1);add(2,month=2);add(1,month=2,lifecycle_status='cancelled')
    add(1,month=2,end_date=None)
    add(1,year=2099)
    add(None,month=3)
    db.session.commit()
    return add


def report(actors,role='director',**kwargs):
    args=MultiDict(dict({'year':'2025','period':'annual','activity_name':'Line fixture'},**kwargs))
    return workspace_report(Event.query,args,db.session.get(User,actors[role]),local_now())


def reconcile(data):
    assert [sum(s['values'][i] for s in data['delivery_series']) for i in range(len(data['monthly']))]==data['monthly']


def test_two_campuses_share_bins_and_keep_zero_periods(actors,deliveries):
    data=report(actors,campus=['1','2'])
    assert [s['name'] for s in data['delivery_series']]==['Lingayen','Urdaneta']
    assert [s['values'][:3] for s in data['delivery_series']]==[[2,0,0],[0,1,0]]
    assert all(len(s['values'])==12 for s in data['delivery_series'])
    reconcile(data)


@pytest.mark.parametrize('selected,mode', [(['1'],'include'),(['3'],'include'),(['1'],'exclude'),([str(i) for i in range(1,10)],'exclude')])
def test_include_exclude_zero_and_unassigned(actors,deliveries,selected,mode):
    data=report(actors,campus=selected,campus_mode=mode)
    reconcile(data)
    if mode=='exclude':assert any(s['name']=='Unassigned' for s in data['delivery_series'])
    if selected==['3']:assert len(data['delivery_series'])==1 and sum(data['monthly'])==0


def test_yearly_bins_use_same_values(actors,deliveries):
    data=report(actors,campus=['1','2'],period='custom',start_date='2020-01-01',end_date='2025-12-31')
    assert data['month_labels']==[str(y) for y in range(2020,2026)]
    assert [s['values'][-1] for s in data['delivery_series']]==[2,1]
    reconcile(data)


def test_no_comparison_and_coordinator_keep_aggregate(actors,deliveries):
    assert report(actors)['delivery_series']==[]
    data=report(actors,role='coordinator',campus=['2'],campus_id='2')
    assert data['delivery_series']==[] and data['campus_id']==1
    assert sum(data['monthly'])==2


def test_legacy_intersection_and_other_filters_remain(actors,deliveries):
    data=report(actors,campus=['1','2'],campus_id='1',sex='female',category='Environment')
    assert [s['id'] for s in data['delivery_series']]==[1]
    reconcile(data)


def test_more_than_page_aggregates_without_query_growth(client,app,actors,deliveries):
    sign_in(client,actors,'director')
    user=db.session.get(User,actors['director'])
    args=MultiDict(dict(year='2025',period='annual',activity_name='Line fixture',campus=['1','2']))
    with query_count(app) as before:workspace_report(Event.query,args,user,local_now())
    for i in range(30):deliveries(1 if i%2 else 2,month=2)
    db.session.commit()
    with query_count(app) as after:data=workspace_report(Event.query,args,user,local_now())
    assert len(after)<=len(before)+1
    reconcile(data)
    response,context=screen(client,app,'/workspace/reports/results?year=2025&activity_name=Line+fixture&campus=1&campus=2&view=activities&page=2')
    assert response.status_code==200 and len(context['rows'])<25
    assert sum(sum(s['values']) for s in context['delivery_series'])==33


@pytest.mark.parametrize('campus',['','1'])
def test_top_filter_submission_clears_comparison(client,actors,deliveries,campus):
    sign_in(client,actors,'director')
    html=parse_html(client.get('/workspace/reports/results?year=2025&campus=1&campus=2&campus_mode=include&sex=female').text)
    values=form_values(form_with_control(html,'period',tags=('select',)))
    assert not {'campus','campus_mode','page'} & values.keys()
    values['campus_id']=[campus]
    response=client.get('/workspace/reports/results',query_string=[(k,v) for k,vs in values.items() for v in vs])
    assert response.status_code==200
    assert 'data-chart-series=\'[]\'' in response.text


def test_comparison_submission_replaces_top_campus_and_starts_closed(client,actors,deliveries):
    sign_in(client,actors,'director')
    html=parse_html(client.get('/workspace/reports/results?year=2025&campus_id=1&sex=female').text)
    dropdown=next(d for d in html.all('details') if 'data-comparison-dropdown' in d.attrs)
    assert 'open' not in dropdown.attrs
    form=form_with_control(dropdown,'campus_mode')
    values=form_values(form)
    assert 'campus_id' not in values and values['sex']==['female'] and values['page']==['1']
    values['campus']=['1','2']
    response=client.get(form.attrs['action'],query_string=[(k,v) for k,vs in values.items() for v in vs])
    assert response.status_code==200 and 'One line per campus' in response.text
