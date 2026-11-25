"""Connected roster UX preserves scope, recording windows and named imports."""
import io
from datetime import timedelta
from urllib.parse import urlsplit, parse_qs
import pytest
from app.models import db
from app.models.event import Event,Registration,Attendance
from app.models.workspace import ExternalGroup
from app.services.activity_workflow import local_now
from tests.test_app import app,client,_create_user
from tests.test_workspace_overhaul import actors,sign_in
from tests.html_helpers import parse_html


@pytest.fixture
def ongoing(app,actors):
    event=db.session.get(Event,1)
    now=local_now();event.date=now-timedelta(hours=1);event.end_date=now+timedelta(hours=1);event.lifecycle_status='approved'
    reg=Registration(event_id=1,user_id=actors['volunteer'],status='confirmed')
    db.session.add(reg);db.session.commit()
    return reg.id


def test_connected_entry_and_preserved_filter_context(client,actors,ongoing):
    sign_in(client,actors)
    response=client.get('/workspace/activities/1/external?q=Person&attendance_status=unmarked&page=2&return_to=/workspace/activities?state=ongoing')
    tree=parse_html(response.text).one('main',id='main-content')
    add=next(a for a in tree.all('a') if a.text=='Add External Participants')
    assert urlsplit(add.attrs['href']).path=='/workspace/activities/1/external/new'
    assert parse_qs(urlsplit(add.attrs['href']).query)['attendance_status']==['unmarked']
    assert not tree.all('textarea',name='roster')
    entry=parse_html(client.get(add.attrs['href']).text).one('main',id='main-content')
    form=entry.one('form',**{'data-roster-entry':None})
    assert 'data-no-draft' in form.attrs
    assert form.one('input',name='csrf_token')
    response=client.post(form.attrs['action'],data={'group_name':'Authored Group','roster':'Person One,one@example.org\nPerson Two'})
    assert response.status_code==302
    query=parse_qs(urlsplit(response.location).query)
    assert query['q']==['Person'] and query['attendance_status']==['unmarked'] and query['page']==['2']
    assert query['return_to']==['/workspace/activities?state=ongoing']
    group=ExternalGroup.query.one();assert group.name=='Authored Group'
    rows=Registration.query.filter(Registration.external_participant_id.isnot(None)).all()
    assert len(rows)==2 and all(r.attendance_record is None for r in rows)


def test_entry_errors_retain_ordinary_values_and_file_guidance(client,actors,ongoing):
    sign_in(client,actors)
    response=client.post('/workspace/activities/1/external/new',data={'group_name':'Preserve & Name','roster':'','mark_present':'yes'})
    assert response.status_code==200
    tree=parse_html(response.text)
    assert tree.one('input',name='group_name').attrs['value']=='Preserve & Name'
    assert tree.one('input',name='mark_present').attrs.get('checked') is not None or 'checked' in tree.one('input',name='mark_present').attrs
    assert 'roster' in [a.attrs.get('href','').removeprefix('#') for a in tree.all('a')]
    assert 'Files must be selected again' in tree.text
    assert ExternalGroup.query.count()==0
    response=client.post('/workspace/activities/1/external/new',data={'group_name':'Retained','roster_file':(io.BytesIO(b'\xff\xff'),'bad.csv')})
    assert response.status_code==400 and b'Retained' in response.data
    assert b'Use a UTF-8 CSV file' in response.data


@pytest.mark.parametrize('path',['/workspace/activities/1/external/new','/workspace/activities/1/external'])
def test_csv_precedence_mark_present_and_legacy_posts(client,actors,ongoing,path):
    sign_in(client,actors)
    response=client.post(path,data={'roster':'Ignored Typed Name','roster_file':(io.BytesIO(b'\xef\xbb\xbfCSV Person,csv@example.org\nSecond Person'),'people.csv'),'mark_present':'yes'})
    assert response.status_code==302
    rows=Registration.query.filter(Registration.external_participant_id.isnot(None)).all()
    assert {r.external_participant.name for r in rows}=={'CSV Person','Second Person'}
    assert all(r.attendance_record.status=='present' for r in rows)


@pytest.mark.parametrize('phase',['upcoming','ended','cancelled','missing'])
def test_readonly_states_have_text_and_no_save_controls(client,actors,ongoing,phase):
    sign_in(client,actors)
    event=db.session.get(Event,1);now=local_now()
    if phase=='upcoming':event.date=now+timedelta(hours=1);event.end_date=now+timedelta(hours=2)
    elif phase=='ended':event.date=now-timedelta(hours=2);event.end_date=now-timedelta(hours=1)
    elif phase=='cancelled':event.lifecycle_status='cancelled'
    else:event.end_date=None
    db.session.add(Attendance(registration_id=ongoing,event_id=1,user_id=actors['volunteer'],status='excused'));db.session.commit()
    for path in ['/attendance?event_id=1','/workspace/activities/1/external','/workspace/activities/1/external/new']:
        response=client.get(path);assert response.status_code==200
        tree=parse_html(response.text).one('main',id='main-content')
        assert not tree.all('select',name='status')
        if phase=='upcoming' and path.endswith('/new'):
            assert tree.one('button',type='submit').text=='Save Named Roster'
            assert not tree.all('input',name='mark_present')
        else:
            assert not [b for b in tree.all('button') if b.text.startswith('Save')]
        assert 'View Registrations' in tree.text if phase=='upcoming' else 'Open Combined Report' in tree.text
    if phase!='upcoming':assert 'Excused' in client.get('/attendance?event_id=1').text
    assert client.post('/workspace/activities/1/external/new',data={'roster':'Named Person'}).status_code==(302 if phase=='upcoming' else 409)
    assert ExternalGroup.query.count()==(1 if phase=='upcoming' else 0)


def test_recorded_choices_cannot_misleadingly_clear_but_blank_post_unchanged(client,actors,ongoing):
    sign_in(client,actors)
    db.session.add(Attendance(registration_id=ongoing,event_id=1,user_id=actors['volunteer'],status='present'));db.session.commit()
    tree=parse_html(client.get('/attendance?event_id=1').text)
    select=tree.one('select',name='status')
    assert '' not in [o.attrs['value'] for o in select.all('option')]
    response=client.post('/attendance?event_id=1',data={'event_id':'1','registration_id':str(ongoing),'status':''})
    assert response.status_code==302 and db.session.get(Registration,ongoing).attendance_record.status=='present'
    assert 'only to the people displayed' in tree.text


@pytest.mark.parametrize('role',['director','volunteer','other'])
def test_new_entry_role_and_campus_restrictions(client,actors,ongoing,role):
    sign_in(client,actors,role)
    expected=404 if role=='other' else 403
    assert client.get('/workspace/activities/1/external/new').status_code==expected
    assert client.post('/workspace/activities/1/external/new',data={'roster':'No Access'}).status_code==expected
    if role=='director':
        response=client.get('/workspace/activities/1/registrations')
        assert response.status_code==200 and 'Report Help' in response.text


def test_safe_return_csrf_and_foreign_ids(client,app,actors,ongoing):
    sign_in(client,actors)
    tree=parse_html(client.get('/workspace/activities/1/external/new?return_to=//outside.example').text).one('main',id='main-content')
    assert '//outside.example' not in tree.one('form',**{'data-roster-entry':None}).attrs['action']
    assert client.post('/attendance?event_id=1',data={'event_id':'1','registration_id':'999999','status':'present'}).status_code==403
    assert client.post('/workspace/activities/1/external',data={'action':'attendance','registration_id':str(ongoing),'status':'present'}).status_code==403
    app.config['WTF_CSRF_ENABLED']=True
    assert client.post('/workspace/activities/1/external/new',data={'roster':'Blocked CSRF'}).status_code==400


@pytest.mark.parametrize('when,allowed',[('start',True),('end',False)])
def test_exact_boundaries_and_final_recheck(client,actors,ongoing,monkeypatch,when,allowed):
    sign_in(client,actors)
    event=db.session.get(Event,1)
    clock=event.date if when=='start' else event.end_date
    from app.services.activity_workflow import attendance_open,external_registration_open
    monkeypatch.setattr('app.routes.workspace.attendance_open',lambda e:attendance_open(e,clock))
    monkeypatch.setattr('app.routes.workspace.external_registration_open',lambda e:external_registration_open(e,clock))
    response=client.post('/workspace/activities/1/external/new',data={'roster':'Boundary Person'})
    assert response.status_code==(302 if allowed else 409)
    assert ExternalGroup.query.count()==(1 if allowed else 0)


def test_roster_ends_before_commit_rolls_back_every_person(client,actors,ongoing,monkeypatch):
    sign_in(client,actors)
    calls=iter([True,False])
    monkeypatch.setattr('app.routes.workspace.attendance_open',lambda e:next(calls))
    response=client.post('/workspace/activities/1/external/new',data={'roster':'First Person\nSecond Person','mark_present':'yes'})
    assert response.status_code==409 and ExternalGroup.query.count()==0
    assert Registration.query.filter(Registration.external_participant_id.isnot(None)).count()==0
    assert b'First Person' in response.data and b'Unsubmitted Participants' in response.data


def test_internal_final_recheck_rolls_back_every_write(client,actors,ongoing,monkeypatch):
    sign_in(client,actors)
    calls=iter([True,False])
    monkeypatch.setattr('app.routes.coordinator.attendance_open',lambda e,*args:next(calls))
    response=client.post('/attendance?event_id=1',data={'event_id':'1','registration_id':str(ongoing),'status':'present'})
    assert response.status_code==409
    assert Attendance.query.count()==0 and db.session.get(Registration,ongoing).status=='confirmed'


@pytest.mark.parametrize('when,allowed',[('start',True),('end',False)])
def test_internal_exact_boundaries(client,actors,ongoing,monkeypatch,when,allowed):
    sign_in(client,actors)
    event=db.session.get(Event,1);clock=event.date if when=='start' else event.end_date
    from app.services.activity_workflow import attendance_open
    monkeypatch.setattr('app.routes.coordinator.attendance_open',lambda e,*args:attendance_open(e,clock))
    response=client.post('/attendance?event_id=1',data={'event_id':'1','registration_id':str(ongoing),'status':'present'})
    assert response.status_code==302
    assert Attendance.query.count()==(1 if allowed else 0)


def test_external_existing_record_final_recheck_and_invalid_batches(client,actors,ongoing,monkeypatch):
    sign_in(client,actors)
    client.post('/workspace/activities/1/external/new',data={'roster':'External Participant'})
    row=Registration.query.filter(Registration.external_participant_id.isnot(None)).one()
    url='/workspace/activities/1/external'
    assert client.post(url,data={'action':'attendance','registration_id':[str(row.id)]*2,'status':['present']*2}).status_code==400
    assert client.post(url,data={'action':'attendance','registration_id':str(row.id),'status':'invalid'}).status_code==400
    calls=iter([True,False]);monkeypatch.setattr('app.routes.workspace.attendance_open',lambda e:next(calls))
    response=client.post(url,data={'action':'attendance','registration_id':str(row.id),'status':'present'})
    assert response.status_code==409 and Attendance.query.count()==0


def test_literal_search_highlighting_and_empty_filters(client,app,actors,ongoing):
    from app.models.user import User
    sign_in(client,actors)
    user=db.session.get(User,actors['volunteer']);user.name='Authored 100%_ <Name>'
    plain=_create_user(app,email='plain@rosters.test',campus_id=1,name='Plain Name')
    db.session.add(Registration(event_id=1,user_id=plain,status='confirmed'));db.session.commit()
    for path,param in [('/attendance','volunteer_search'),('/workspace/activities/1/registrations','q')]:
        query={param:'%_'}
        if path=='/attendance':query['event_id']=1
        response=client.get(path,query_string=query)
        table=parse_html(response.text).one('table',**{'class':'roster-table'})
        assert 'Authored 100%_ <Name>' in table.text and 'Plain Name' not in table.text
        assert '<mark>%_</mark>' in response.text and '&lt;Name&gt;' in response.text
    client.post('/workspace/activities/1/external/new',data={'roster':'External 100%_\nOther External'})
    response=client.get('/workspace/activities/1/external',query_string={'q':'%_'})
    table=parse_html(response.text).one('table',**{'class':'roster-table'})
    assert 'External 100%_' in table.text and 'Other External' not in table.text
    response=client.get('/workspace/activities/1/external?attendance_status=present')
    assert 'No Matching External Volunteers' in response.text
