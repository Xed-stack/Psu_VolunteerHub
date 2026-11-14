"""Behavioral acceptance for the connected UI and activity workflow."""
import io
import zipfile
from datetime import timedelta
import pytest
from app.models import db
from app.models.user import User, Skill, Interest, VolunteerProfile
from app.models.event import Event, Registration, Attendance
from app.models.workspace import FormDraft
from app.services.activity_workflow import attendance_open, local_now
from tests.test_app import app, client


@pytest.fixture
def actors(app, tmp_path):
    app.config['PRIVATE_UPLOAD_FOLDER'] = str(tmp_path)
    with app.app_context():
        people = {}
        for role, campus in [('director', 1), ('coordinator', 1), ('volunteer', 1), ('other', 2)]:
            user = User(name=role, email=f'{role}@example.org', role='coordinator' if role == 'other' else role,
                        campus_id=campus, sex='prefer_not_to_say')
            user.set_password('Strong-pass123!')
            db.session.add(user)
            db.session.flush()
            people[role] = user.id
        db.session.commit()
        return people


def sign_in(client, actors, role='coordinator'):
    from flask import g
    g.pop('_login_user', None)
    with client.session_transaction() as session:
        session['_user_id'] = str(actors[role])
        session['_fresh'] = True
        session['auth_version'] = 1


@pytest.mark.parametrize('path', ['/workspace/overview', '/workspace/activities', '/workspace/reports',
    '/workspace/reports/results', '/workspace/reports/aop', '/workspace/create/1',
    '/workspace/partners', '/workspace/drafts', '/workspace/volunteers', '/workspace/reports/historical', '/workspace/activities/1', '/workspace/activities/1/registrations', '/workspace/activities/1/documents',
    '/workspace/activities/1/external', '/attendance?event_id=1'])
def test_connected_coordinator_screens_render(client, actors, path):
    sign_in(client, actors)
    response = client.get(path)
    assert response.status_code == 200, response.data[:1000]


@pytest.mark.parametrize('path', ['/workspace/overview', '/workspace/imports', '/workspace/imports/annual',
    '/workspace/imports/historical', '/admin_dash', '/settings', '/workspace/management', '/workspace/categories'])
def test_director_has_merged_permissions(client, actors, path):
    sign_in(client, actors, 'director')
    assert client.get(path).status_code == 200


def test_draft_refresh_private_scope_and_secrets(client, app, actors):
    sign_in(client, actors)
    key = '/workspace/drafts/activity:new'
    assert client.put(key, json={'title': ['Retained title'], 'password': ['never'], 'consent': ['on'], '_proposal': {'path': 'forged'}}).status_code == 200
    payload = client.get(key).json['payload']
    assert payload == {'title': ['Retained title']}
    sign_in(client, actors, 'other')
    assert client.get(key).json['payload'] == {}
    sign_in(client, actors)
    assert client.get(key).json['payload']['title'] == ['Retained title']
    with app.app_context():
        db.session.get(User, actors['coordinator']).campus_id = 2
        db.session.commit()
    sign_in(client, actors)
    assert client.get(key).status_code == 403


def test_draft_discard_and_bad_shape(client, actors):
    sign_in(client, actors)
    key = '/workspace/drafts/form:/settings'
    assert client.put(key, json={'name': ['Remember']}).status_code == 200
    assert client.put(key, json={'name': [{'nested': 'invalid'}]}).status_code == 400
    assert client.delete(key).status_code == 204
    assert client.get(key).json['payload'] == {}


def docx():
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Title: Campus learning day</w:t></w:r></w:p></w:body></w:document>')
    output.seek(0)
    return output


def test_proposal_extract_resume_and_publish(client, app, actors):
    sign_in(client, actors)
    response = client.post('/workspace/create/1', data={'proposal': (docx(), 'approved.docx')})
    assert response.status_code == 302
    assert b'Campus learning day' in client.get('/workspace/create/2').data
    with app.app_context():
        event = Event.query.first()
        category = event.category
    start = local_now() + timedelta(days=10)
    details = {'title': 'Campus learning day', 'description': 'Learning together', 'category': category,
               'date': start.isoformat(timespec='minutes'), 'end_date': (start + timedelta(hours=2)).isoformat(timespec='minutes'),
               'slots': '20', 'cancellation_days': '2'}
    assert client.post('/workspace/create/2', data=details).status_code == 302
    assert client.post('/workspace/create/3', data={'participant_type': 'Students'}).status_code == 302
    assert client.get('/workspace/create/4').status_code == 200
    response = client.post('/workspace/create/4')
    assert response.status_code == 302, response.data[:1000]
    with app.app_context():
        event = Event.query.filter_by(title='Campus learning day').one()
        assert event.proposal_document['name'] == 'approved.docx'
        assert event.lifecycle_status == 'approved'
        assert FormDraft.query.filter_by(user_id=actors['coordinator'], key='activity:new').count() == 0
        assert client.get(f'/workspace/activities/{event.id}/proposal').status_code == 200
    sign_in(client, actors, 'other')
    assert client.get(f'/workspace/activities/{event.id}/proposal').status_code == 404


def test_no_proposal_or_past_schedule_cannot_publish(client, actors):
    sign_in(client, actors)
    assert client.get('/workspace/create/4').status_code == 302
    client.post('/workspace/create/1', data={'proposal': (docx(), 'approved.docx')})
    client.post('/workspace/create/2', data={'title':'Past', 'description':'No', 'date':'2020-01-01T09:00', 'end_date':'2020-01-01T10:00', 'category':'Environment', 'slots':'10'})
    assert b'future start' in client.post('/workspace/create/4').data


@pytest.mark.parametrize('phase', ['future', 'ongoing', 'ended', 'legacy', 'cancelled'])
def test_attendance_window_server_and_external(client, app, actors, phase):
    sign_in(client, actors)
    with app.app_context():
        event = db.session.get(Event, 1)
        now = local_now()
        event.date = now + timedelta(hours=1) if phase == 'future' else now - timedelta(hours=2)
        event.end_date = None if phase == 'legacy' else now - timedelta(hours=1) if phase == 'ended' else now + timedelta(hours=1)
        event.lifecycle_status = 'cancelled' if phase == 'cancelled' else 'approved'
        reg = Registration(user_id=actors['volunteer'], event_id=1, status='confirmed')
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.id
        assert attendance_open(event) == (phase == 'ongoing')
    response = client.post('/attendance', data={'event_id':'1','registration_id':str(reg_id),'status':'present'})
    assert response.status_code == 302
    with app.app_context():
        assert Attendance.query.filter_by(registration_id=reg_id).count() == (1 if phase == 'ongoing' else 0)
    response = client.post('/workspace/activities/1/external', data={'roster':'Named person,person@example.org','mark_present':'yes'})
    assert response.status_code == (302 if phase == 'ongoing' else 409)


def test_cancellation_preserves_activity_and_blocks_join(client, app, actors):
    sign_in(client, actors)
    assert client.post('/workspace/activities/1/cancel', data={'reason':'Campus closure'}).status_code == 302
    with app.app_context():
        assert db.session.get(Event, 1).lifecycle_status == 'cancelled'
    assert client.post('/coordinator/events/1/delete').status_code == 405
    sign_in(client, actors, 'volunteer')
    assert client.post('/opportunities/register/1').status_code == 302
    with app.app_context():
        assert Registration.query.filter_by(event_id=1).count() == 0


@pytest.mark.parametrize('format', ['csv','pdf','xlsx'])
def test_report_exports(client, actors, format):
    sign_in(client, actors)
    response = client.get('/workspace/reports/export/' + format)
    assert response.status_code == 200
    assert response.data


def test_volunteer_screens_and_private_registration(client, app, actors):
    sign_in(client, actors, 'volunteer')
    for path in ['/volunteer_dash','/workspace/registrations','/opportunities','/profile?section=preferences','/profile?section=impact']:
        assert client.get(path).status_code == 200
    assert client.get('/workspace/overview').status_code == 403
    assert client.get('/workspace/registrations/987').status_code == 404


def test_direct_withdrawal_does_not_create_request(client, app, actors):
    with app.app_context():
        registration = Registration(event_id=1, user_id=actors['volunteer'], status='confirmed')
        db.session.add(registration)
        db.session.commit()
        reg_id = registration.id
    sign_in(client, actors, 'volunteer')
    assert client.post(f'/registrations/{reg_id}/cancel').status_code == 302
    with app.app_context():
        row = db.session.get(Registration, reg_id)
        assert row.status == 'cancelled'
        assert row.cancellation_request is None


def test_general_upload_restore_and_secret_exclusion(client, app, actors):
    sign_in(client, actors)
    response = client.post('/workspace/draft-uploads/form:/example', data={
        'field':'document', 'upload':(docx(),'saved.docx')})
    assert response.status_code == 200
    payload = client.get('/workspace/drafts/form:/example').json['payload']
    assert payload['_files']['document']['name'] == 'saved.docx'
    sign_in(client, actors, 'other')
    assert client.get('/workspace/drafts/form:/example').json['payload'] == {}


def test_saved_proposal_can_continue_without_reupload(client, actors):
    sign_in(client, actors)
    client.post('/workspace/create/1',data={'proposal':(docx(),'approved.docx')})
    response = client.post('/workspace/create/1')
    assert response.status_code == 302
    assert response.location.endswith('/2')


def test_external_existing_attendance_edit_is_time_locked(client, app, actors):
    sign_in(client, actors)
    with app.app_context():
        event = db.session.get(Event,1)
        event.date = local_now()-timedelta(hours=1)
        event.end_date = local_now()+timedelta(hours=1)
        db.session.commit()
    client.post('/workspace/activities/1/external',data={'roster':'A Person,person@example.org','mark_present':'yes'})
    with app.app_context():
        reg = Registration.query.filter_by(event_id=1).one()
        reg_id = reg.id
    response = client.post('/workspace/activities/1/external',data={'action':'attendance','registration_id':str(reg_id),'status':'absent'})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Registration,reg_id).attendance_record.status == 'absent'
        db.session.get(Event,1).end_date = local_now()-timedelta(minutes=1)
        db.session.commit()
    assert client.post('/workspace/activities/1/external',data={'action':'attendance','registration_id':str(reg_id),'status':'present'}).status_code == 409


def test_confirmation_required_for_user_import(client, app, actors):
    sign_in(client, actors,'director')
    from app.routes.admin import USER_IMPORT_COLUMNS
    import csv
    output = io.StringIO()
    writer = csv.DictWriter(output,fieldnames=USER_IMPORT_COLUMNS)
    writer.writeheader()
    writer.writerow({'name':'Imported volunteer','email':'new@example.org','password':'StrongPassword1!','role':'volunteer','campus_code':'LINGAYEN'})
    response = client.post('/admin/users/import',data={'file':(io.BytesIO(output.getvalue().encode()),'users.csv')})
    assert response.status_code == 200
    assert b'Review User Import' in response.data
    with app.app_context():
        assert User.query.filter_by(email='new@example.org').count() == 0
    with client.session_transaction() as session:
        token = session['user_import_preview']['token']
    response = client.post('/admin/users/import',data={'action':'confirm','token':token})
    assert response.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email='new@example.org').count() == 1


@pytest.mark.parametrize('format', ['csv', 'xlsx', 'pdf'])
def test_aop_exports(client, actors, format):
    sign_in(client, actors)
    assert client.get('/workspace/reports/export/' + format + '?report=aop').status_code == 200


def test_recorded_presence_derives_completion_without_late_write(app, actors):
    from app.reports import build_events_report
    with app.app_context():
        event = db.session.get(Event, 1)
        event.date = local_now() - timedelta(hours=2)
        event.end_date = local_now() - timedelta(hours=1)
        registration = Registration(user_id=actors['volunteer'], event_id=event.id, status='confirmed')
        db.session.add(registration)
        db.session.flush()
        db.session.add(Attendance(registration_id=registration.id, event_id=event.id, status='present'))
        db.session.commit()
        assert registration.certificate_eligible
        rows, _ = build_events_report(event_id=event.id, now=local_now())
        assert rows[0]['verified_completed'] == 1
        assert rows[0]['attendance_complete']
        assert registration.status == 'confirmed'


def test_saved_attachment_is_restored_on_submission_and_draft_cleared(client, app, actors):
    sign_in(client, actors)
    from app.models.workspace import PartnerAgency, PartnerAgreement
    with app.app_context():
        agency = PartnerAgency(name='Partner',contact_name='Contact',campus_id=1)
        db.session.add(agency)
        db.session.commit()
        agency_id = agency.id
    key = f'form:/workspace/partners/{agency_id}'
    assert client.post('/workspace/draft-uploads/'+key,data={'field':'document','upload':(docx(),'agreement.docx')}).status_code == 200
    response = client.post(f'/workspace/partners/{agency_id}',data={'_draft_key':key,'reference':'MOA-1','valid_from':'2026-01-01','valid_until':'2030-12-31'})
    assert response.status_code == 302
    with app.app_context():
        assert PartnerAgreement.query.one().document['name'] == 'agreement.docx'
        assert FormDraft.query.filter_by(user_id=actors['coordinator'],key=key).count() == 0


def test_recommendations_only_match_interests_and_prioritize_home_campus(app, actors):
    from app.recommendation.engine import get_recommendations
    with app.app_context():
        user = db.session.get(User,actors['volunteer'])
        interest = Interest(name='Environment')
        db.session.add(interest)
        user.interests = [interest]
        profile = VolunteerProfile(user_id=user.id)
        db.session.add(profile)
        events = []
        for title,category,campus,status in [('Home','Environment',1,'approved'),('Away','Environment',2,'approved'),
                                              ('Unrelated','Arts & Culture',1,'approved'),('Cancelled','Environment',1,'cancelled')]:
            event = Event(title=title,description=title,category=category,campus_id=campus,lifecycle_status=status,
                          date=local_now()+timedelta(days=7),end_date=local_now()+timedelta(days=7,hours=2),slots=20)
            db.session.add(event)
            events.append(event)
        db.session.commit()
        rows = get_recommendations(profile,events,top_n=10,campus_id=1,commit=False)
        assert [row['event'].title for row in rows] == ['Home','Away']
        assert all(row['score'] > 0 for row in rows)


def test_missing_interests_do_not_produce_unrelated_recommendations(app, actors):
    from app.recommendation.engine import get_recommendations
    with app.app_context():
        profile = VolunteerProfile(user_id=actors['volunteer'])
        db.session.add(profile)
        db.session.commit()
        assert get_recommendations(profile) == []
        assert get_recommendations(None) == []
