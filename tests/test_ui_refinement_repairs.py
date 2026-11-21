"""Acceptance for activity refinements and evidence-preserving attendance defaults."""
import io
from datetime import timedelta
import pytest
from werkzeug.datastructures import MultiDict
from pypdf import PdfReader
from app.models import db
from app.models.event import Event, Registration, Attendance, ExternalParticipant
from app.models.workspace import ActivityProposal, PartnerAgency
from app.services.activity_workflow import local_now
from app.services.attendance_state import state, activation_time, roster_filter
from app.services.activity_fields import partner_count
from tests.test_app import app, client
from tests.test_workspace_overhaul import actors, sign_in
from tests.test_proposal_record import seed_draft, complete_record
from tests.test_activity_forms import details, choices


@pytest.mark.parametrize('value,total,agency,expected', [('',None,None,None),('0',None,None,0),('12',20,1,12),('999999999',None,1,999999999)])
def test_partner_count_accepts_planning_estimates(value,total,agency,expected):
    assert partner_count(value,total,agency)==expected


@pytest.mark.parametrize('value,total,agency', [('1',None,None),('21',20,1),('-1',20,1),('1.5',20,1),('1000000000',None,1),('１',None,1)])
def test_partner_count_rejects_invalid_or_unassociated_estimates(value,total,agency):
    with pytest.raises(ValueError):partner_count(value,total,agency)


def test_draft_can_remain_incomplete_but_continue_validates(client,actors):
    draft=seed_draft(client,actors)
    response=client.post('/workspace/create/2',data={'title':'Retain this title','date':'bad','save_step':'3'})
    assert response.status_code==200 and b'Check the Proposal' in response.data
    assert draft.payload['title']==['Retain this title']
    response=client.post('/workspace/create/2',data={'description':'Incomplete but saved','save_draft':'yes'})
    assert response.status_code==302 and response.location.endswith('/create/2')
    assert draft.payload['description']==['Incomplete but saved']
    response=client.post('/workspace/create/2',data={'save_step':'1'})
    assert response.status_code==302 and response.location.endswith('/create/1')
    html=client.get('/workspace/create/2').text
    assert 'proposal-disclosure' in html and 'Complete' in html.split('id="section-purpose"')[1].split('</summary>')[0]
    assert 'id="schedule-picker-date" required' not in html
    assert 'data-schedule-label="date"' in html
    assert 'Public Activity Description *' in html


def test_blank_first_step_save_is_allowed(client,actors):
    sign_in(client,actors)
    client.get('/workspace/create/1')
    response=client.post('/workspace/create/1',data={'save_draft':'yes'})
    assert response.status_code==302 and response.location.endswith('/create/1')


def test_partner_estimate_publishes_and_preserves_other_audience_data(client,actors):
    record=complete_record()
    agency=PartnerAgency(name='Primary Agency',contact_name='Primary Contact',campus_id=1)
    db.session.add(agency);db.session.commit()
    record.update(partnership_status='new',agency_id=str(agency.id),psu_roles='Teach',partner_roles='Host',partnership_duration='One day')
    draft=seed_draft(client,actors,record)
    draft.payload=dict(draft.payload,target_participants=['100'],expected_partner_participants=['25']);db.session.commit()
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes','capture_confirmed':list(draft.payload['_capture'])})
    assert response.status_code==302,response.text
    event=Event.query.filter_by(title='Published proposal').one()
    assert event.audience['expected_partner_participants']==25
    assert event.audience['expected_partner_agency_id']==agency.id
    assert event.audience['departments']==[]
    assert db.session.get(ActivityProposal,event.id).publishing_snapshot['Expected Partner Participants']==['25']


def test_default_absence_filters_reports_and_exports_without_evidence(client,app,actors):
    now=local_now()
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=(now-timedelta(days=2)).isoformat()+'+08:00'
    event=db.session.get(Event,1)
    event.date=now-timedelta(days=1);event.end_date=now-timedelta(hours=1);event.lifecycle_status='approved'
    external=ExternalParticipant(id_number='default-external',name='Default External')
    db.session.add(external);db.session.flush()
    internal=Registration(event_id=1,user_id=actors['volunteer'],status='confirmed')
    outsider=Registration(event_id=1,external_participant_id=external.id,status='completed')
    db.session.add_all([internal,outsider]);db.session.commit()
    assert state(internal)==dict(status='absent',basis='system_default')
    assert state(outsider)['basis']=='system_default'
    assert not internal.certificate_eligible and Attendance.query.count()==0
    assert roster_filter(Registration.query,'absent',event).count()==2
    assert roster_filter(Registration.query,'unmarked',event).count()==0
    from app.services.workspace_reports import _activity_rows
    from app.reports import build_events_report
    rows=_activity_rows(Event.query.filter_by(id=1),MultiDict(),now)
    assert rows[0]['metrics']['defaulted']==2 and rows[0]['metrics']['missing']==0
    legacy,_=build_events_report(event_id=1,now=now)
    assert legacy[0]['defaulted_attendance']==2
    from app.reports import render_csv, render_pdf, _build_meta
    legacy_rows,summary=build_events_report(event_id=1,now=now)
    meta=_build_meta('Default Attendance','Lingayen',None,None,None)
    assert 'Not Attended (System Default)' in render_csv(legacy_rows,summary,meta)
    legacy_pdf=render_pdf(legacy_rows,summary,meta)
    assert 'System Default' in ' '.join(page.extract_text() for page in PdfReader(io.BytesIO(legacy_pdf)).pages)
    sign_in(client,actors)
    for path in ['/attendance?event_id=1&attendance_status=absent','/workspace/activities/1/external?attendance_status=absent','/workspace/reports/activities/1?period=all']:
        response=client.get(path)
        assert response.status_code==200 and b'Not Attended (System Default)' in response.data,(path,response.status_code)
    csv=client.get('/workspace/reports/export/csv?period=all&event_id=1')
    assert csv.status_code==200 and b'system_default' in csv.data and b'Not Attended (System Default)' in csv.data
    from openpyxl import load_workbook
    workbook=client.get('/workspace/reports/export/xlsx?period=all&event_id=1')
    assert workbook.status_code==200
    book=load_workbook(io.BytesIO(workbook.data))
    assert any('system_default' in row for sheet in book for row in sheet.values)
    pdf=client.get('/workspace/reports/export/pdf?period=all&event_id=1')
    assert pdf.status_code==200
    text=' '.join(' '.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.data)).pages).split())
    assert 'System Default' in text and 'Default External' in text
    assert Attendance.query.count()==0
    db.session.add(Attendance(registration_id=internal.id,event_id=1,user_id=internal.user_id,status='excused'));db.session.commit();db.session.expire_all()
    assert state(internal)==dict(status='excused',basis='recorded')


def test_activation_boundaries_and_registration_exclusions(app,actors):
    now=local_now();event=db.session.get(Event,1)
    event.lifecycle_status='approved';event.date=now-timedelta(days=4);event.end_date=now-timedelta(days=1)
    reg=Registration(event=event,user_id=actors['volunteer'],status='confirmed');db.session.add(reg);db.session.commit()
    for activation in [None,event.end_date.isoformat()+'+08:00',(event.end_date+timedelta(seconds=1)).isoformat()+'+08:00']:
        app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=activation
        assert state(reg)['basis']=='unrecorded'
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=(event.end_date-timedelta(seconds=1)).isoformat()+'+08:00'
    assert state(reg)['basis']=='system_default'
    for status in ['pending','cancelled']:
        reg.status=status;assert state(reg)['basis']=='unrecorded'
    reg.status='confirmed';event.end_date=None
    assert state(reg)['basis']=='unrecorded'
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']='2026-11-21T12:00:00'
    with pytest.raises(ValueError):activation_time()


def test_edit_partner_estimate_department_scope_and_locked_event(client,actors):
    sign_in(client,actors)
    _,sdgs=choices();event=db.session.get(Event,1)
    event.date=local_now()+timedelta(days=10);event.end_date=event.date+timedelta(hours=2);event.lifecycle_status='approved'
    event.conducting_department='Preserved old department'
    event.audience={'departments':['Preserved notification department'],'volunteer_ids':[actors['volunteer']]}
    agency=PartnerAgency(name='Edit Primary',contact_name='Contact',campus_id=1)
    db.session.add(agency);db.session.flush()
    db.session.add(ActivityProposal(event_id=event.id,agency_id=agency.id,content=complete_record()))
    db.session.commit()
    form=dict(details(event,sdgs),target_participants='60',expected_partner_participants='20',conducting_department=event.conducting_department)
    path=f'/coordinator/events/{event.id}/edit'
    assert client.post(path,data=form).status_code==302
    assert event.audience['expected_partner_participants']==20
    assert event.audience['volunteer_ids']==[actors['volunteer']]
    response=client.post(path,data=dict(form,conducting_department='Forged campus department'))
    assert b'Choose a Conducting Department from your campus list.' in response.data
    assert event.conducting_department=='Preserved old department'
    response=client.post(path,data=dict(form,expected_partner_participants='61'))
    assert b'cannot exceed the Total Participant Target' in response.data
    assert event.audience['expected_partner_participants']==20
    event.date=local_now()-timedelta(days=1);event.end_date=local_now()-timedelta(hours=1);db.session.commit()
    assert client.post(path,data=form).status_code==409


def test_annual_evidence_button_and_overview_read_only_action(client,actors):
    sign_in(client,actors)
    response=client.get('/annual-goals/workspace?year=2025&campus=2')
    assert response.status_code==200
    assert b'View Lingayen Annual Evidence' in response.data and b'Back to Annual Evidence' not in response.data
    assert b'campus=1' in response.data
    event=db.session.get(Event,1);event.lifecycle_status='approved'
    event.date=local_now()-timedelta(days=1);event.end_date=local_now()-timedelta(hours=1)
    db.session.add(Registration(event_id=1,user_id=actors['volunteer'],status='confirmed'));db.session.commit()
    overview=client.get('/workspace/overview?period=all').text
    assert 'Open Correction Report' not in overview
    assert 'Attendance is locked. Historical unrecorded values remain unchanged.' in overview
