"""Verified evidence must reconcile across staff screens and downloads."""
import csv
import io
from datetime import timedelta

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader
from werkzeug.datastructures import MultiDict

from app.models import db
from app.models.event import Attendance, Event, ExternalParticipant, Registration
from app.models.user import User
from app.services.activity_workflow import local_now
from app.services.workspace_reports import SEX_LABELS, _activity_rows, workspace_report
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_ui_reimagining import screen
from tests.test_system_performance import query_count


@pytest.fixture
def evidence(app, actors):
    now = local_now()
    def activity(title, campus=1, **changes):
        values = dict(title='Breakdown ' + title, description='Synthetic evidence', campus_id=campus,
                      date=now-timedelta(days=2), end_date=now-timedelta(days=1),
                      lifecycle_status='approved', category='Environment', conducting_department='Extension')
        values.update(changes)
        event = Event(**values); db.session.add(event); db.session.flush()
        return event
    def record(event, participant, status='confirmed', attendance='present'):
        reg = Registration(event_id=event.id, status=status, **(
            {'user_id': participant.id} if isinstance(participant, User) else {'external_participant_id': participant.id}))
        db.session.add(reg); db.session.flush()
        if attendance:
            db.session.add(Attendance(event_id=event.id, registration_id=reg.id, status=attendance))
    primary = activity('primary')
    people = []
    for i, sex in enumerate(['female','male','prefer_not_to_say',None]):
        user = User(name=f'PSU {i}', email=f'breakdown-{i}@example.test', password_hash='unused',
                    role='volunteer', campus_id=1, sex=sex, college_affiliation='College A')
        external = ExternalParticipant(name=f'External {i}', id_number=f'breakdown-{i}', sex=sex)
        db.session.add_all([user,external]); db.session.flush()
        record(primary,user); record(primary,external,status='completed'); people.extend([user,external])
    for i,(status,attendance) in enumerate([('pending','present'),('cancelled','present'),('confirmed','absent'),('confirmed',None)]):
        person=ExternalParticipant(id_number=f'excluded-{i}',sex='female');db.session.add(person);db.session.flush()
        record(primary,person,status,attendance)
    repeat = activity('repeat'); record(repeat,people[0])
    other = activity('other',campus=2); record(other,people[1])
    for title,changes in [
        ('ongoing',dict(date=now-timedelta(hours=1),end_date=now+timedelta(hours=1))),
        ('future',dict(date=now+timedelta(days=1),end_date=now+timedelta(days=2))),
        ('unknown',dict(end_date=None)),('cancelled',dict(lifecycle_status='cancelled')),
        ('draft',dict(lifecycle_status='draft'))]:
        record(activity(title,**changes),people[0])
    db.session.commit()
    return dict(primary=primary,repeat=repeat,other=other,people=people,now=now,record=record,activity=activity)


def report(actors, role='director', **args):
    user=db.session.get(User,actors[role])
    return workspace_report(Event.query,MultiDict(dict(period='all',activity_name='Breakdown',**args)),user,local_now())


def test_verified_summary_excludes_unverified_evidence_and_keeps_unknown_sex(app,actors,evidence):
    data=report(actors)
    assert data['attendees']==data['sex_breakdown']['total']==10
    groups=data['sex_breakdown']['groups']
    assert [(g['psu'],g['external'],g['total'],g['share']) for g in groups]==[
        (2,2,4,40.0),(1,1,2,20.0),(1,1,2,20.0),(1,1,2,20.0)]
    assert [g['label'] for g in groups]==list(SEX_LABELS.values())
    for row in data['rows']:
        assert sum(sum(counts.values()) for counts in row['sex_counts'].values())==(row['attendees'] if row['conducted'] else 0)
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=(evidence['now']-timedelta(days=10)).isoformat()+'+08:00'
    defaulted=report(actors)
    assert defaulted['sex_breakdown']==data['sex_breakdown']
    assert next(r for r in defaulted['rows'] if r['event'].id==evidence['primary'].id)['metrics']['defaulted']==1


@pytest.mark.parametrize('sex,total', [('female',4),('male',2),('prefer_not_to_say',2),('unrecorded',2)])
def test_sex_filters_include_both_participant_types(app,actors,evidence,sex,total):
    data=report(actors,sex=sex)
    assert data['attendees']==data['sex_breakdown']['total']==total
    assert next(g for g in data['sex_breakdown']['groups'] if g['key']==sex)['total']==total
    assert sum(g['external'] for g in data['sex_breakdown']['groups'])>0
    assert all(r['metrics']['target_met'] is None for r in data['rows'])


def test_affiliation_scope_and_coordinator_cannot_be_broadened(app,actors,evidence):
    data=report(actors,'coordinator',campus_id='2',campus='2',campus_mode='exclude')
    assert data['campus_id']==1 and data['attendees']==9
    assert data['sex_breakdown']['total']==9
    data=report(actors,sex='female',affiliation='College A')
    assert data['attendees']==2 and sum(g['external'] for g in data['sex_breakdown']['groups'])==0


def test_empty_and_date_search_department_filters(app,actors,evidence):
    data=report(actors,category='No match')
    assert data['sex_breakdown']['total']==0 and all(g['share'] is None for g in data['sex_breakdown']['groups'])
    day=evidence['primary'].date.date().isoformat()
    user=db.session.get(User,actors['director'])
    args=MultiDict(dict(period='custom',start_date=day,end_date=day,activity_name='Breakdown primary',department='Extension',sex='female'))
    data=workspace_report(Event.query,args,user,local_now())
    assert data['attendees']==2 and len(data['rows'])==1
    args['start_date']=args['end_date']=(evidence['primary'].date.date()+timedelta(days=1)).isoformat()
    assert workspace_report(Event.query,args,user,local_now())['sex_breakdown']['total']==0


def test_screen_totals_precede_pagination_and_match_exports(client,app,actors,evidence):
    for i in range(26):
        evidence['record'](evidence['activity'](f'page {i}'),evidence['people'][0])
    db.session.commit();sign_in(client,actors,'director')
    query='?period=all&activity_name=Breakdown'
    _,overview=screen(client,app,'/workspace/overview'+query)
    for view in ['summary','participation','activities']:
        response,data=screen(client,app,'/workspace/reports/results'+query+'&view='+view+'&page=2')
        assert len(data['rows'])<data['total']
        assert data['sex_breakdown']['total']==overview['attendees']==36
        assert (b'Sex-Disaggregated Verified Attendance' in response.data)==(view!='activities')
    response=client.get('/workspace/reports/export/csv'+query)
    rows=list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'))))
    for key,label in SEX_LABELS.items():
        assert sum(int(r['Verified Attendance: '+label]) for r in rows)==next(g['total'] for g in overview['sex_breakdown']['groups'] if g['key']==key)
    response=client.get('/workspace/reports/export/xlsx'+query)
    book=load_workbook(io.BytesIO(response.data));sheet=book['Verified Attendance by Sex']
    assert sheet['D6'].value==36 and sheet['D2'].value==30
    assert book['Activities'].max_row==len(rows)+1
    pdf=client.get('/workspace/reports/export/pdf'+query)
    assert pdf.status_code==200
    text='\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.data)).pages)
    assert 'Sex-Disaggregated Verified Attendance' in text and 'Not Recorded' in text
    assert '30.0%' not in text and '83.3%' in text


def test_combined_activity_scope_and_overview_commitments(client,app,actors,evidence):
    sign_in(client,actors,'director')
    response,data=screen(client,app,'/workspace/overview?period=all')
    from tests.html_helpers import parse_html
    commitments=parse_html(response.text).one('table',**{'class':'director-commitments-table'})
    assert len(commitments.all('tr'))==10
    response,data=screen(client,app,f'/workspace/reports/activities/{evidence["primary"].id}?period=all&sex=female')
    assert data['sex_breakdown']['total']==2 and data['roster'].total==5
    assert b'Sex-Disaggregated Verified Attendance' in response.data
    sign_in(client,actors,'other')
    assert client.get(f'/workspace/reports/activities/{evidence["primary"].id}').status_code==404


def test_aggregation_query_count_stays_constant(app,actors,evidence):
    args=MultiDict()
    with query_count(app) as small:
        _activity_rows(Event.query,args,local_now())
    for i in range(30):
        evidence['record'](evidence['activity'](f'query {i}'),evidence['people'][0])
    db.session.commit();db.session.expire_all()
    with query_count(app) as large:
        _activity_rows(Event.query,args,local_now())
    assert len(large)==len(small)==3
