"""Advance named registration never supplies early attendance evidence."""
import io
from datetime import timedelta
import pytest
from app.models import db
from app.models.event import Event,Registration,Attendance,ExternalParticipant
from app.models.workspace import ExternalGroup
from app.services.activity_workflow import local_now,external_registration_open
from tests.test_workspace_overhaul import app,client,actors,sign_in


@pytest.mark.parametrize('missing_end',[False,True])
def test_advance_registration_from_attendance_and_external_pages(client,app,actors,missing_end):
    sign_in(client,actors)
    event=db.session.get(Event,1);now=local_now()
    event.date=now+timedelta(hours=1)
    event.end_date=None if missing_end else now+timedelta(hours=2)
    event.lifecycle_status='approved';db.session.commit()
    for url in ('/attendance?event_id=1','/workspace/activities/1/external'):
        body=client.get(url).text
        assert 'Add External Participants' in body
        assert 'Save Attendance' not in body and 'Save External Attendance' not in body
    form=client.get('/workspace/activities/1/external/new').text
    assert 'Save Named Roster' in form and 'name="mark_present"' not in form
    assert 'Registration only' in form
    if missing_end:assert 'Edit Activity Schedule' in form
    forged=client.post('/workspace/activities/1/external/new',data={'roster':'Early Presence','mark_present':'yes'})
    assert forged.status_code==409 and ExternalGroup.query.count()==0
    response=client.post('/workspace/activities/1/external/new',data={
        'group_name':'Advance Group','roster_file':(io.BytesIO(b'Advance One,one@example.invalid\nAdvance Two'),'roster.csv')})
    assert response.status_code==302
    registrations=Registration.query.filter(Registration.external_participant_id.isnot(None)).all()
    assert len(registrations)==2 and all(row.status=='confirmed' and row.attendance_record is None for row in registrations)
    assert Attendance.query.count()==0
    row=registrations[0]
    assert client.post('/workspace/activities/1/external',data={'action':'attendance','registration_id':str(row.id),'status':'present'}).status_code==409
    assert Attendance.query.count()==0
    event.date=now-timedelta(hours=1);event.end_date=now+timedelta(hours=1);db.session.commit()
    assert client.post('/workspace/activities/1/external',data={'action':'attendance','registration_id':str(row.id),'status':'present'}).status_code==302
    assert Attendance.query.filter_by(registration_id=row.id,status='present').count()==1
    event.end_date=now-timedelta(minutes=1);db.session.commit()
    assert client.post('/workspace/activities/1/external/new',data={'roster':'Late Person'}).status_code==409
    assert client.post('/workspace/activities/1/external',data={'action':'attendance','registration_id':str(row.id),'status':'absent'}).status_code==409
    assert Attendance.query.filter_by(registration_id=row.id,status='present').count()==1


def test_advance_registration_race_rolls_back_people_and_groups(client,app,actors,monkeypatch):
    sign_in(client,actors)
    event=db.session.get(Event,1);event.date=local_now()+timedelta(hours=1);event.end_date=None
    event.lifecycle_status='approved';db.session.commit()
    before=(ExternalParticipant.query.count(),Registration.query.count(),ExternalGroup.query.count())
    calls=iter([True,False])
    monkeypatch.setattr('app.routes.workspace.external_registration_open',lambda event:next(calls))
    response=client.post('/workspace/activities/1/external/new',data={'roster':'Retained Name','group_name':'Retained Group'})
    assert response.status_code==409 and 'Retained Name' in response.text and 'Unsubmitted Participants' in response.text
    assert before==(ExternalParticipant.query.count(),Registration.query.count(),ExternalGroup.query.count())


def test_registration_window_states(app,actors):
    now=local_now();event=db.session.get(Event,1)
    event.lifecycle_status='approved';event.date=now+timedelta(hours=1);event.end_date=None
    assert external_registration_open(event,now)
    event.date=now
    assert not external_registration_open(event,now)
    event.end_date=now+timedelta(hours=1)
    assert external_registration_open(event,now)
    assert not external_registration_open(event,event.end_date)
    event.lifecycle_status='cancelled'
    assert not external_registration_open(event,now)
