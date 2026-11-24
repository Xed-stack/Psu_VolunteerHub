"""Report finalization is scoped, read-only and separate from review evidence."""
import csv
import io
from datetime import timedelta
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader
from app.models import db
from app.models.event import Event,Registration,Attendance,ExternalParticipant,SdgGoal
from app.models.user import User
from app.services.activity_workflow import local_now
from app.services.workspace_reports import participation_outcome,workspace_report
from werkzeug.datastructures import MultiDict
from tests.test_workspace_overhaul import app,client,actors,sign_in
from tests.test_ui_reimagining import screen


@pytest.mark.parametrize('present,registrations,target,unrecorded,rate,outcome',[
    (0,4,3,4,0,'Target Not Met'),(2,4,3,2,50,'Target Not Met'),
    (3,4,3,1,75,'Target Met'),(4,4,3,0,100,'Target Met'),
    (0,0,3,0,None,'Target Not Met'),(0,0,None,0,None,'Target Not Set'),
])
def test_ended_outcomes_include_unrecorded_denominator(present,registrations,target,unrecorded,rate,outcome):
    event=SimpleNamespace(target_participants=target)
    result=participation_outcome(event,dict(present=present,registrations=registrations),True,present,unrecorded)
    assert result['rate']==rate and result['target_label']==outcome
    assert result['rate_label']==('No Registrations' if rate is None else str(float(rate))+'%')


@pytest.fixture
def report_case(app,actors):
    now=local_now()
    user=db.session.get(User,actors['volunteer'])
    user.sex='female';user.college_affiliation='Report College'
    second=User(name='Report Female',email='report-female@example.invalid',role='volunteer',campus_id=1,
        sex='female',college_affiliation='Report College',password_hash='unused')
    male=ExternalParticipant(name='Report Male',id_number='report-male',sex='male')
    female=ExternalParticipant(name='Report External',id_number='report-female',sex='female')
    cancelled=ExternalParticipant(name='Cancelled Report',id_number='report-cancelled',sex='female')
    db.session.add_all([second,male,female,cancelled]);db.session.flush()
    events={}
    for name,start,end,status,campus in [
        ('Primary',now-timedelta(days=2),now-timedelta(days=1),'approved',1),
        ('Unrecorded',now-timedelta(days=2),now-timedelta(days=1),'approved',1),
        ('Ongoing',now-timedelta(hours=1),now+timedelta(hours=1),'approved',1),
        ('Upcoming',now+timedelta(days=1),now+timedelta(days=2),'approved',1),
        ('Missing End',now-timedelta(days=1),None,'approved',1),
        ('Boundary',now-timedelta(hours=1),now,'approved',1),
        ('Draft',now-timedelta(days=2),now-timedelta(days=1),'draft',1),
        ('Cancelled',now-timedelta(days=2),now-timedelta(days=1),'cancelled',1),
        ('Other Campus',now-timedelta(days=2),now-timedelta(days=1),'approved',2),
    ]:
        event=Event(title='Report Fix '+name,description='Synthetic',date=start,end_date=end,
            lifecycle_status=status,campus_id=campus,category='Environment',conducting_department='Extension',target_participants=2)
        db.session.add(event);db.session.flush();events[name]=event
    sdgs=SdgGoal.query.order_by(SdgGoal.number).limit(2).all()
    if not sdgs:
        sdgs=[SdgGoal(number=1,name='No Poverty'),SdgGoal(number=2,name='Zero Hunger')]
        db.session.add_all(sdgs)
        db.session.flush()
    events['Primary'].sdgs=sdgs
    for participant,status,attendance in [(user,'confirmed','present'),(male,'completed','present'),
        (second,'confirmed',None),(female,'confirmed',None),(cancelled,'cancelled','present')]:
        reg=Registration(event_id=events['Primary'].id,status=status,**({'user_id':participant.id} if isinstance(participant,User) else {'external_participant_id':participant.id}))
        db.session.add(reg);db.session.flush()
        if attendance:db.session.add(Attendance(event_id=events['Primary'].id,registration_id=reg.id,status=attendance))
    db.session.add(Registration(event_id=events['Unrecorded'].id,user_id=user.id,status='confirmed'))
    db.session.commit()
    return events,now,sdgs


@pytest.mark.parametrize('role',['director','coordinator'])
def test_delivery_scope_sdgs_and_combined_filters(client,app,actors,report_case,role):
    events,now,sdgs=report_case
    sign_in(client,actors,role)
    args=MultiDict(dict(period='all',activity_name='Report Fix',campus_id='1'))
    actor=db.session.get(User,actors[role])
    args['delivery']='approved'
    data=workspace_report(Event.query,args,actor,now)
    assert {row['event'].id for row in data['rows']}=={events[name].id for name in ('Ongoing','Upcoming','Missing End')}
    args['delivery']='conducted'
    data=workspace_report(Event.query,args,actor,now)
    assert {row['event'].id for row in data['rows']}=={events[name].id for name in ('Primary','Unrecorded','Boundary')}
    response,data=screen(client,app,f'/workspace/reports/results?period=all&view=activities&activity_name=Report+Fix&campus_id=1&delivery=conducted&category=Environment&department=Extension&sdg_id={sdgs[0].id}&sex=female')
    assert data['total']==1 and data['rows'][0]['event'].id==events['Primary'].id
    assert all(f'SDG {sdg.number}: {sdg.name}' in response.text for sdg in sdgs)
    _,empty=screen(client,app,'/workspace/reports/results?period=all&activity_name=Report+Fix&affiliation=Unlisted')
    assert empty['total']==0
    assert client.get('/workspace/reports/results?event_id=bad').status_code==400
    if role=='coordinator':
        _,locked=screen(client,app,'/workspace/reports/results?period=all&activity_name=Report+Fix&campus_id=2')
        assert all(row['event'].campus_id==1 for row in locked['rows'])


@pytest.mark.parametrize('role',['director','coordinator'])
def test_finalized_outcomes_and_exports_preserve_raw_evidence(client,app,actors,report_case,role):
    events,now,sdgs=report_case
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=None
    sign_in(client,actors,role)
    before=(Registration.query.count(),Attendance.query.count())
    query='period=all&activity_name=Report+Fix+Primary&sex=female'
    response,data=screen(client,app,'/workspace/reports/results?view=participation&'+query)
    row=data['rows'][0]
    assert row['metrics']['registrations']==3 and row['metrics']['present']==1
    assert not row['metrics']['complete'] and row['metrics']['rate'] is None and row['metrics']['target_met'] is None
    assert row['participation']['rate']==33.3 and row['participation']['target_met'] is True
    assert row['participation']['whole_present']==2 and row['participation']['unrecorded']==2
    assert 'Target Met' in response.text and 'Ended · 2 Unrecorded' in response.text
    export=client.get('/workspace/reports/export/csv?'+query)
    exported=list(csv.DictReader(io.StringIO(export.data.decode('utf-8-sig'))))[0]
    assert exported['Attendance rate (%)']=='33.3' and exported['Target outcome']=='Target Met'
    assert exported['Whole-activity recorded present']=='2'
    book=load_workbook(io.BytesIO(client.get('/workspace/reports/export/xlsx?'+query).data))
    assert list(book['Activities'].values)[1][0]==events['Primary'].title
    pdf=client.get('/workspace/reports/export/pdf?'+query)
    assert pdf.data.startswith(b'%PDF') and 'Target Met' in ''.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.data)).pages)
    _,combined=screen(client,app,f'/workspace/reports/activities/{events["Primary"].id}?period=all&sex=female')
    assert combined['roster'].total==3
    _,missing=screen(client,app,'/workspace/reports/results?period=all&activity_name=Report+Fix+Unrecorded')
    assert missing['rows'][0]['participation']['rate']==0 and missing['rows'][0]['participation']['target_label']=='Target Not Met'
    assert before==(Registration.query.count(),Attendance.query.count())
