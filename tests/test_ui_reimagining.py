"""Restored capabilities must use current lifecycle, scope, and draft rules."""
import csv
import io
import json
from datetime import timedelta
from pathlib import Path

from flask import template_rendered
from PIL import Image
from openpyxl import load_workbook

from app.models import db
from app.models.event import Event, Registration, Attendance, HistoricalActivity, CancellationRequest, SdgGoal
from app.models.notification import Notification
from app.models.workspace import FormDraft
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app, client, actors, sign_in, docx


def screen(client,app,path):
    contexts=[]
    def capture(sender,template,context,**extra):
        contexts.append(context.copy())
    template_rendered.connect(capture,app)
    try:
        response=client.get(path)
        assert response.status_code == 200,response.data[:1000]
        return response,contexts[-1]
    finally:
        template_rendered.disconnect(capture,app)


def test_restored_destinations_and_permissions(client,app,actors):
    sign_in(client,actors,'director')
    for path in ['/workspace/overview','/director/calendar','/workspace/campuses/1',
                 '/workspace/recognition','/workspace/reports/people','/workspace/follow-up']:
        response,_=screen(client,app,path)
        assert b'aria-label="Quick Navigation"' in response.data
    sign_in(client,actors)
    for path in ['/coordinator/calendar','/workspace/follow-up','/workspace/reports/people']:
        screen(client,app,path)
    assert client.get('/workspace/recognition').status_code == 403
    assert client.get('/workspace/campuses/2').status_code == 403
    sign_in(client,actors,'volunteer')
    assert client.get('/workspace/follow-up').status_code == 403
    assert client.get('/workspace/reports/people').status_code == 403


def test_periods_filters_and_export_values_agree(client,app,actors):
    sign_in(client,actors)
    event=Event.query.first()
    event.title='Literal 100%_service'
    event.date=local_now()-timedelta(days=3)
    event.end_date=event.date+timedelta(hours=2)
    event.target_participants=2
    event.conducting_department='Authorized department'
    reg=Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed')
    db.session.add(reg);db.session.flush()
    db.session.add(Attendance(registration_id=reg.id,event_id=event.id,status='present'))
    db.session.commit()
    query='?period=all&activity_name=100%25_&department=Authorized+department'
    _,data=screen(client,app,'/workspace/reports/results'+query)
    assert len(data['rows']) == 1
    metrics=data['rows'][0]['metrics']
    assert metrics['registrations'] == metrics['present'] == metrics['completed'] == 1
    assert metrics['rate'] == 100 and metrics['target_met'] is False
    assert data['deltas'] == {}
    csv_response=client.get('/workspace/reports/export/csv'+query)
    row=list(csv.DictReader(io.StringIO(csv_response.data.decode('utf-8-sig'))))[0]
    assert row['Registrations'] == '1' and row['Completed participation'] == '1'
    assert row['Attendance rate (%)'] == '100.0' and row['Numeric participant target'] == '2'
    book=load_workbook(io.BytesIO(client.get('/workspace/reports/export/xlsx'+query).data))
    assert book['Activities'].max_row == 2 and len(book['Delivery trend']._charts) == 1
    assert client.get('/workspace/reports/export/pdf'+query).data.startswith(b'%PDF')
    assert client.get('/workspace/reports/results?period=custom&start_date=2026-02-02&end_date=2026-01-01').status_code == 400
    assert client.get('/workspace/reports/results?period=custom&start_date=bad&end_date=bad').status_code == 400


def test_multiple_campuses_and_multi_year_bins(client,app,actors):
    sign_in(client,actors,'director')
    rows=Event.query.order_by(Event.id).limit(3).all()
    for i,row in enumerate(rows):
        row.title='Scope fixture '+str(i)
        row.date=local_now().replace(year=2023+i,month=1,day=10)
        row.end_date=row.date+timedelta(hours=1)
        row.campus_id=1 if i<2 else 2
    db.session.commit()
    _,data=screen(client,app,'/workspace/reports/results?period=all&activity_name=Scope+fixture&campus=1&campus=2')
    assert len(data['rows']) == 3
    assert len(set(data['month_labels'])) == len(data['month_labels'])
    assert sum(data['monthly']) == 3
    _,data=screen(client,app,'/workspace/reports/results?period=all&activity_name=Scope+fixture&campus=2&campus_mode=exclude')
    assert {r['event'].campus_id for r in data['rows']} == {1}
    sign_in(client,actors)
    _,data=screen(client,app,'/workspace/reports/results?period=all&activity_name=Scope+fixture&campus_id=2')
    assert {r['event'].campus_id for r in data['rows']} == {1}


def test_pending_evidence_never_becomes_a_rate_and_reminders_deduplicate(client,app,actors):
    sign_in(client,actors,'director')
    event=Event.query.first();event.date=local_now()-timedelta(days=1);event.end_date=local_now()-timedelta(hours=1)
    event.target_participants=20
    db.session.add(Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed'));db.session.commit()
    _,data=screen(client,app,f'/workspace/reports/results?period=all&event_id={event.id}')
    assert data['rows'][0]['metrics']['rate'] is None
    assert data['rows'][0]['metrics']['target_met'] is None
    payload=dict(follow_up_campus_id='1',goal_year=str(local_now().year),guidance_kind='pending_attendance',
                 guidance_event_id=str(event.id),report_scope=json.dumps({'year':[str(local_now().year)],'period':['all']}))
    assert client.post('/director/campus-follow-up',data=payload).status_code == 302
    assert client.post('/director/campus-follow-up',data=payload).status_code == 302
    assert Notification.query.filter_by(user_id=actors['coordinator'],notification_type='campus_guidance').count() == 1
    assert Notification.query.filter_by(user_id=actors['other'],notification_type='campus_guidance').count() == 0
    event.end_date=None;db.session.commit()
    _,data=screen(client,app,f'/workspace/reports/results?period=all&event_id={event.id}')
    assert data['rows'][0]['attention'] == ['schedule_limit']
    assert data['rows'][0]['metrics']['rate'] is None


def test_legacy_links_keep_their_scope(client,actors):
    sign_in(client,actors,'director')
    response=client.get('/analytics?event_id=1&campus=1&campus=2&category=Environment&department=Faculty&start_date=2025-01-01&end_date=2025-12-31')
    from urllib.parse import urlsplit,parse_qs
    location=urlsplit(response.location)
    assert location.path == '/workspace/reports/results'
    query=parse_qs(location.query)
    assert query['campus'] == ['1','2'] and query['event_id'] == ['1'] and query['period'] == ['custom']
    assert query['affiliation'] == ['Faculty'] and 'department' not in query
    assert parse_qs(urlsplit(client.get('/analytics?view=historical&start_year=2020&end_year=2025').location).query)['start_year'] == ['2020']


def test_historical_scope_unknown_counts_and_exports(client,app,actors):
    sign_in(client,actors)
    for i in range(3):
        db.session.add(HistoricalActivity(source_key='restore-'+str(i),source_document='Institutional source',source_page=1,
            source_row=i+1,unit_name='Unit '+str(i),campus_id=1 if i<2 else 2,title='Historical fixture '+str(i),
            activity_type='Extension',volunteer_count=None if i==0 else 5,year_conducted=2021+i))
    db.session.commit()
    query='?start_year=2021&end_year=2023&activity_type=Extension&q=Historical+fixture'
    _,data=screen(client,app,'/workspace/reports/historical'+query)
    assert data['pagination'].total == 2
    assert any(r['count'] is None for r in data['historical_chart'])
    for format in ('csv','xlsx','pdf'):
        response=client.get('/workspace/reports/historical/export/'+format+query)
        assert response.status_code == 200
        if format == 'csv':
            assert b'Historical fixture 2' not in response.data and b'Unknown' in response.data
    assert client.get('/workspace/reports/historical?start_year=2025&end_year=2020').status_code == 400


def test_registration_filters_deadline_and_read_only_decision(client,app,actors):
    sign_in(client,actors,'volunteer')
    event=Event.query.first(); event.date=local_now()+timedelta(days=10);event.cancellation_deadline=local_now()+timedelta(days=8)
    reg=Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed')
    db.session.add(reg);db.session.flush()
    db.session.add(CancellationRequest(registration_id=reg.id,reason='Other',status='rejected',review_note='Preserved decision'))
    db.session.commit()
    response=client.get(f'/workspace/registration-invalid')
    assert response.status_code == 404
    response=client.get(f'/workspace/registrations/{reg.id}')
    assert b'Preserved decision' in response.data and b'Withdrawal Deadline' in response.data
    assert event.cancellation_deadline.strftime('%d %b %Y, %I:%M %p').encode() in response.data
    assert client.get(f'/registrations/{reg.id}/cancel').status_code == 200
    assert b'Withdrawal Deadline' in client.get(f'/registrations/{reg.id}/cancel').data
    _,data=screen(client,app,'/workspace/registrations?campus=2')
    assert data['pagination'].total == 0
    event.cancellation_deadline=local_now()-timedelta(minutes=1);db.session.commit()
    assert b'The withdrawal deadline has passed.' in client.get(f'/workspace/registrations/{reg.id}').data


def test_prepublication_cover_restores_and_removed_options_are_ignored(client,app,actors,tmp_path):
    sign_in(client,actors)
    app.static_folder=str(tmp_path/'public')
    assert client.post('/workspace/create/1',data={'proposal':(docx(),'approved.docx')}).status_code == 302
    event=Event.query.first();future=local_now()+timedelta(days=12)
    details=dict(title='Restored publishing options',description='Test activity',category=event.category,slots='5',
                 date=future.isoformat(timespec='minutes'),end_date=(future+timedelta(hours=1)).isoformat(timespec='minutes'))
    sdg=SdgGoal.query.first()
    if sdg:details['sdg_ids']=[str(sdg.id)]
    client.post('/workspace/create/2',data=details)
    image=io.BytesIO();Image.new('RGB',(8,8),'blue').save(image,format='PNG');image.seek(0)
    assert client.post('/workspace/draft-uploads/activity:new',data={'field':'cover_image','upload':(image,'cover.png')}).status_code == 200
    draft=FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').one()
    staged=Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'draft-uploads'/draft.payload['_files']['cover_image']['path']
    client.post('/workspace/create/3',data={'nda_required':'on','nda_text':'Keep private records confidential.'})
    response=client.get('/workspace/create/2')
    assert b'cover.png' in response.data and b'Keep private records confidential.' not in response.data
    assert client.post('/workspace/create/4').status_code == 302
    published=Event.query.filter_by(title=details['title']).one()
    assert not published.nda_required and published.nda_version is None and published.cover_image_path
    assert (Path(app.static_folder)/published.cover_image_path).is_file()
    assert not staged.exists()
    assert FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').count() == 0
