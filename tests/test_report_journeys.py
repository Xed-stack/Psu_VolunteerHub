"""Connected report screens must preserve authoritative scopes and evidence."""
import csv
import io
from datetime import timedelta
from html import unescape
from urllib.parse import urlencode,parse_qs,urlsplit

from openpyxl import load_workbook
from app.models import db
from app.models.event import Event,Registration,Attendance
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app,client,actors,sign_in
from tests.test_ui_reimagining import screen
from tests.test_annual_goals import target


def test_views_preserve_scope_and_export_dataset(client,app,actors):
    sign_in(client,actors)
    event=Event.query.first();event.title='Authored 100%_Activity';event.date=local_now()-timedelta(days=1);event.end_date=event.date+timedelta(hours=1);db.session.commit()
    query='?period=all&campus=1&campus=2&activity_name=100%25_'
    for view in ['summary','activities','participation','invalid']:
        response,data=screen(client,app,'/workspace/reports/results'+query+'&view='+view)
        assert data['report_view']==('summary' if view=='invalid' else view)
        assert data['total']==1
        if view in ('summary','invalid'):
            assert b'Activity Delivery and Proposals</h2>' not in response.data
            assert b'Participation Measures"' not in response.data
        elif view=='activities':assert b'Activity Delivery and Proposals</h2>' in response.data
        else:assert b'Numeric Targets</h2>' in response.data
        assert 'campus=1&amp;campus=2' in response.text
    for view in ['summary','activities','participation']:
        rows=list(csv.DictReader(io.StringIO(client.get('/workspace/reports/export/csv'+query+'&view='+view).data.decode('utf-8-sig'))))
        assert len(rows)==1 and rows[0]['Activity']=='Authored 100%_Activity'
    sign_in(client,actors,'director')
    redirect=client.get('/analytics'+query+'&view=participation')
    assert parse_qs(urlsplit(redirect.location).query)['view']==['participation']


def test_combined_report_forces_event_and_keeps_full_roster(client,app,actors):
    sign_in(client,actors)
    event=Event.query.first();event.date=local_now()-timedelta(days=2);event.end_date=event.date+timedelta(hours=1)
    reg=Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed');db.session.add(reg);db.session.flush();db.session.add(Attendance(event_id=event.id,registration_id=reg.id,status='present'));db.session.commit()
    origin='/workspace/reports/results?period=all&view=participation&campus=1&campus=2&page=1'
    query='?'+urlencode({'return_to':origin,'event_id':'999','sex':'female'})
    response,data=screen(client,app,f'/workspace/reports/activities/{event.id}'+query)
    assert data['event_id']==event.id and data['row']['metrics']['present']==0
    assert data['roster'].total==1 and b'volunteer' in response.data
    assert 'href="'+origin+'"' in unescape(response.text)
    assert data['export_query']['event_id']==[str(event.id)]
    export=client.get('/workspace/reports/export/xlsx',query_string=[(key,value) for key,values in data['export_query'].items() for value in values])
    book=load_workbook(io.BytesIO(export.data))
    assert book['Named attendance'].max_row==2 and book['Activities'].max_row==2
    sign_in(client,actors,'other');assert client.get(f'/workspace/reports/activities/{event.id}').status_code==404
    sign_in(client,actors,'volunteer');assert client.get(f'/workspace/reports/activities/{event.id}').status_code==403


def test_indicator_shared_members_conflicts_and_permissions(client,app,actors):
    first=target(campus=1,shared='shared',actual=4);second=target(campus=1,kind='ASP',shared='shared',actual=4)
    sign_in(client,actors)
    for item in [first,second]:
        response,data=screen(client,app,f'/annual-goals/targets/{item.id}?campus=2')
        assert data['row']['met'] and data['row']['plan_types']==['AOP','ASP'] and len(data['members'])==2
        assert b'Manage AOP Evidence' not in response.data
    second.results[0].actual_value=3;db.session.commit()
    response,data=screen(client,app,f'/annual-goals/targets/{second.id}')
    assert data['row']['pending'] and b'Shared target evidence conflicts' in response.data
    assert client.get(f'/annual-goals/targets/{first.id}?sample=1').status_code==400
    sign_in(client,actors,'other');assert client.get(f'/annual-goals/targets/{first.id}').status_code==403
    sign_in(client,actors,'director');assert b'Manage AOP Evidence' in client.get(f'/annual-goals/targets/{first.id}').data
    from app.models.user import User
    university=target()
    db.session.get(User,actors['coordinator']).campus_id=None;db.session.commit()
    sign_in(client,actors)
    assert client.get(f'/annual-goals/targets/{university.id}').status_code==403
    assert client.get(f'/annual-goals/targets/{university.id}/activities').status_code==403


def test_annual_rollup_export_and_exact_links(client,app,actors):
    campus=target(campus=1,actual=4,shared='both');target(campus=1,kind='ASP',actual=4,shared='both');target(campus=2)
    university=target(actual=2)
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/reports/aop')
    assert (data['campus_rollup']['total'],data['campus_rollup']['met'],data['campus_rollup']['pending'])==(2,1,1)
    assert data['goals']['total']==1 and data['goals']['met']==0
    assert f'/annual-goals/targets/{university.id}?' in response.text
    response,_=screen(client,app,'/workspace/reports/aop?campus_id=1')
    assert f'/annual-goals/targets/{campus.id}?' in response.text
    book=load_workbook(io.BytesIO(client.get('/workspace/reports/export/xlsx?report=aop').data))
    assert sum(row[1] for row in list(book['Campus obligations'].values)[1:])==1
    assert sum(row[2] for row in list(book['Campus obligations'].values)[1:])==2
    assert len(book['Comparison 1']._charts)==1
    assert b'Campus,Obligations achieved' in client.get('/workspace/reports/export/csv?report=aop').data


def test_indicator_return_context_evidence_and_sample(client,app,actors):
    item=target(campus=1)
    sign_in(client,actors,'director')
    origin='/annual-goals?campus=1&plan=AOP&status=pending&page=1'
    detail=f'/annual-goals/targets/{item.id}?'+urlencode({'return_to':origin})
    response=client.get(detail);assert 'href="'+origin+'"' in unescape(response.text)
    evidence=f'/annual-goals/targets/{item.id}/evidence?'+urlencode({'return_to':detail})
    response=client.post(evidence,data=dict(actual_value='4',source_document='Approved source',coverage_start=f'{local_now().year}-01-01',coverage_end=local_now().date().isoformat(),coverage_note='Approved year-to-date snapshot.',approved='1'))
    assert response.status_code==302 and response.location==detail
    sample=client.get('/annual-goals?sample=1')
    assert b'Sample Data' in sample.data and b'/annual-goals/targets/' not in sample.data
    assert b'Actual Participation by Recorded Sex' not in client.get('/annual-goals').data
