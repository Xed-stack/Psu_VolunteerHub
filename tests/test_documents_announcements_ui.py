"""Documents/update journeys preserve private files, recipients and legacy drafts."""
import io
from pathlib import Path
from datetime import datetime,timedelta
from urllib.parse import quote,urlsplit,parse_qs
import pytest
from sqlalchemy.exc import SQLAlchemyError
from app.models import db
from app.models.event import Event,Milestone,EventAnnouncement,Registration,ExternalParticipant
from app.models.notification import Notification
from app.models.workspace import FormDraft
from tests.test_app import app,client,_create_user
from tests.test_workspace_overhaul import actors,sign_in,docx
from tests.html_helpers import parse_html

DOC='/workspace/activities/1/documents'
UPLOAD=DOC+'/upload'
COMPOSE='/workspace/activities/1/announcements/new'
PDF=b'%PDF-1.4\nSample private evidence'


def stage(client,key,name='evidence.pdf',content=PDF):
    return client.post('/workspace/draft-uploads/'+quote(key,safe=''),data={'field':'file','upload':(io.BytesIO(content),name)})


def test_directory_views_order_pagination_metadata_and_empty(app,client,actors):
    sign_in(client,actors)
    for i in range(27):
        db.session.add(Milestone(event_id=1,filename=f'Authored <File> {i}.pdf',upload_path='uploads/retired.pdf' if i==26 else 'milestones/private.pdf',uploaded_by_id=actors['coordinator'],uploaded_at=datetime(2026,11,16)+timedelta(minutes=i)))
        db.session.add(EventAnnouncement(event_id=1,author_id=None,announcement_type='event_update',message=f'Message {i} <script>alert(1)</script>',created_at=datetime(2026,11,16)+timedelta(minutes=i)))
    db.session.commit()
    page=parse_html(client.get(DOC).text).one('main',id='main-content')
    assert len(page.all('article'))==25
    assert 'Authored <File> 26.pdf' in page.all('article')[0].text
    assert 'Legacy file unavailable' in page.all('article')[0].text
    assert not page.all('article')[0].all('a')
    assert not page.all('form')
    assert len(parse_html(client.get(DOC+'?page=2').text).one('main',id='main-content').all('article'))==2
    response=client.get(DOC+'?view=announcements')
    assert '&lt;script&gt;' in response.text
    page=parse_html(response.text).one('main',id='main-content')
    assert len(page.all('article'))==25 and 'unavailable account' in page.text
    assert not [a for a in page.all('a') if '/milestones/' in a.attrs.get('href','')]
    for invalid in ['','unknown','ALL']:
        response=client.get(DOC,query_string={'view':invalid})
        assert 'Supporting Evidence' in response.text
    Milestone.query.delete();EventAnnouncement.query.delete();db.session.commit()
    assert 'No Supporting Evidence Yet' in client.get(DOC).text
    assert 'No Announcements Yet' in client.get(DOC+'?view=announcements').text


@pytest.mark.parametrize('role',['director','volunteer','other'])
@pytest.mark.parametrize('path',[DOC,UPLOAD,COMPOSE])
def test_form_role_and_campus_scope(client,actors,role,path):
    sign_in(client,actors,role)
    expected=200 if role=='director' and path==DOC else 404 if role=='other' else 403
    assert client.get(path).status_code==expected
    if path!=DOC:assert client.post(path).status_code==(404 if role=='other' else 403)


@pytest.mark.parametrize('legacy',[False,True])
def test_upload_private_storage_download_permissions_and_anchor(app,client,actors,legacy):
    sign_in(client,actors)
    path='/events/1/milestones' if legacy else UPLOAD
    response=client.post(path+'?page=2&return_to=/workspace/activities?state=past',data={'file':(io.BytesIO(PDF),'original evidence.pdf'),'category':'report'})
    assert response.status_code==302
    url=urlsplit(response.location)
    assert url.fragment.startswith('document-') and parse_qs(url.query)['page']==['1']
    assert parse_qs(url.query)['return_to']==['/workspace/activities?state=past']
    row=Milestone.query.one()
    assert row.filename=='original_evidence.pdf' and row.upload_path.startswith('milestones/')
    assert 'original' not in row.upload_path
    download=f'/milestones/{row.id}/download'
    assert client.get(download).data==PDF
    sign_in(client,actors,'other');assert client.get(download).status_code==403
    sign_in(client,actors,'director');assert client.get(download).data==PDF
    sign_in(client,actors,'volunteer');assert client.get(download).status_code==403


@pytest.mark.parametrize('legacy',[False,True])
def test_recipient_rules_and_schedule_notice_do_not_change_activity(app,client,actors,legacy):
    sign_in(client,actors)
    accounts={}
    for status in ['pending','confirmed','completed','cancelled']:
        uid=_create_user(app,email=status+'@updates.test',campus_id=1)
        accounts[status]=uid;db.session.add(Registration(user_id=uid,event_id=1,status=status))
    external=ExternalParticipant(name='External Person',id_number='EXT-UPDATE');db.session.add(external);db.session.flush()
    db.session.add(Registration(external_participant_id=external.id,event_id=1,status='confirmed'));db.session.commit()
    event=db.session.get(Event,1);before=(event.date,event.end_date,event.lifecycle_status)
    response=client.post('/coordinator/events/1/announcements' if legacy else COMPOSE,data={'announcement_type':'cancelled_postponed','message':'  Authored <Update>\nSecond line.  '})
    assert response.status_code==302 and 'view=announcements' in response.location and '#announcement-' in response.location
    assert {n.user_id for n in Notification.query.all()}=={accounts['pending'],accounts['confirmed']}
    assert EventAnnouncement.query.one().message=='Authored <Update>\nSecond line.'
    assert (event.date,event.end_date,event.lifecycle_status)==before


def test_validation_retains_values_drafts_and_no_publication(client,actors):
    sign_in(client,actors)
    response=client.post(COMPOSE,data={'announcement_type':'invalid','message':'Kept <message>'})
    assert response.status_code==400 and '&lt;message&gt;' in response.text
    tree=parse_html(response.text).one('main',id='main-content')
    assert tree.one('textarea',name='message').text=='Kept <message>'
    assert tree.one('a',href='#announcement_type')
    assert client.post(COMPOSE,data={'announcement_type':'event_update','message':'x'*1001}).status_code==400
    assert client.post(COMPOSE,data={'announcement_type':'event_update','message':' '}).status_code==400
    assert EventAnnouncement.query.count()==0 and Notification.query.count()==0
    assert client.post(UPLOAD).status_code==400
    assert client.post(UPLOAD,data={'file':(io.BytesIO(b'not PDF'),'wrong.pdf')}).status_code==400
    assert Milestone.query.count()==0


@pytest.mark.parametrize('first',['upload','announcement'])
def test_legacy_combined_draft_consumes_only_submitted_half(app,client,actors,first):
    sign_in(client,actors)
    key='form:'+DOC+'?draft_form=2'
    assert stage(client,key).status_code==200
    assert client.put('/workspace/drafts/'+quote(key,safe=''),json={'message':['Remaining message'],'announcement_type':['event_update']}).status_code==200
    row=FormDraft.query.one();file=Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'draft-uploads'/row.payload['_files']['file']['path']
    page=client.get(DOC,query_string={'resume':key})
    assert 'Resume Saved Upload' in page.text and 'Resume Saved Announcement' in page.text
    for path in [UPLOAD,COMPOSE]:
        response=client.get(path,query_string={'resume':key})
        assert response.status_code==200 and 'both parts' in response.text
    if first=='upload':
        response=client.post(UPLOAD,data={'_draft_key':key,'category':'report'})
        assert response.status_code==302 and not file.exists()
        assert FormDraft.query.one().payload=={'message':['Remaining message'],'announcement_type':['event_update']}
        assert Milestone.query.count()==1
        response=client.post(COMPOSE,data={'_draft_key':key,'message':'Remaining message','announcement_type':'event_update'})
    else:
        response=client.post(COMPOSE,data={'_draft_key':key,'message':'Remaining message','announcement_type':'event_update'})
        assert response.status_code==302 and file.exists()
        assert '_files' in FormDraft.query.one().payload and 'message' not in FormDraft.query.one().payload
        response=client.post(UPLOAD,data={'_draft_key':key,'category':'report'})
    assert response.status_code==302 and FormDraft.query.count()==0
    assert not file.exists()


def test_canonical_drafts_independent_invalid_replacement_retains_upload(app,client,actors):
    sign_in(client,actors)
    upload_key='form:'+UPLOAD;message_key='form:'+COMPOSE
    assert stage(client,upload_key).status_code==200
    client.put('/workspace/drafts/'+quote(message_key,safe=''),json={'message':['Private unsent message'],'announcement_type':['last_call'],'password':['Never Save'],'accept_terms':['yes']})
    original=FormDraft.query.filter_by(key=upload_key).one().payload['_files']['file']
    file=Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'draft-uploads'/original['path']
    assert stage(client,upload_key,'bad.pdf',b'invalid').status_code==400
    assert FormDraft.query.filter_by(key=upload_key).one().payload['_files']['file']==original and file.exists()
    assert 'Saved attachment: evidence.pdf' in client.get(UPLOAD).text
    assert 'Private unsent message' in client.get(COMPOSE).text
    assert 'Never Save' not in client.get(COMPOSE).text
    assert 'accept_terms' not in FormDraft.query.filter_by(key=message_key).one().payload
    assert client.post(COMPOSE,data={'_draft_key':message_key,'message':'Published','announcement_type':'event_update'}).status_code==302
    assert FormDraft.query.filter_by(key=upload_key).count()==1 and file.exists()


@pytest.mark.parametrize('kind',['upload','announcement'])
def test_failed_commit_rolls_back_and_retains_draft(app,client,actors,kind,monkeypatch):
    sign_in(client,actors)
    key='form:'+(UPLOAD if kind=='upload' else COMPOSE)
    if kind=='upload':stage(client,key)
    else:client.put('/workspace/drafts/'+quote(key,safe=''),json={'message':['Keep me'],'announcement_type':['event_update']})
    def fail():raise SQLAlchemyError('Injected commit failure')
    monkeypatch.setattr(db.session,'commit',fail)
    response=client.post(UPLOAD if kind=='upload' else COMPOSE,data={'_draft_key':key,'message':'Keep me','announcement_type':'event_update','category':'report'})
    assert response.status_code==500
    assert Milestone.query.count()==0 and EventAnnouncement.query.count()==0 and Notification.query.count()==0
    assert FormDraft.query.filter_by(key=key).count()==1
    assert not list((Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'milestones').glob('*'))
    if kind=='upload':assert 'Saved attachment: evidence.pdf' in response.text
    else:assert 'Keep me' in response.text


def test_draft_resume_mismatches_campus_and_forged_return(client,app,actors):
    sign_in(client,actors)
    key='form:'+COMPOSE
    client.put('/workspace/drafts/'+quote(key,safe=''),json={'message':['Private'],'announcement_type':['event_update']})
    assert client.get(UPLOAD,query_string={'resume':key}).status_code==400
    assert client.post(UPLOAD,data={'_draft_key':key,'file':(io.BytesIO(PDF),'test.pdf')}).status_code==400
    assert client.get(COMPOSE,query_string={'resume':'form:/workspace/activities/2/announcements/new'}).status_code==400
    sign_in(client,actors,'other')
    assert client.get(COMPOSE,query_string={'resume':key}).status_code==404
    sign_in(client,actors)
    row=FormDraft.query.filter_by(key=key).one();row.campus_id=2;db.session.commit()
    assert client.get(COMPOSE).status_code==403
    row.campus_id=1;db.session.commit()
    tree=parse_html(client.get(COMPOSE+'?return_to=//outside.example').text).one('main',id='main-content')
    assert '//outside.example' not in tree.one('form').attrs['action']


def test_csrf_file_size_and_no_lifecycle_restriction(app,client,actors):
    sign_in(client,actors)
    app.config['MILESTONE_MAX_BYTES']=10
    assert client.post(UPLOAD,data={'file':(io.BytesIO(PDF),'large.pdf')}).status_code==400
    assert stage(client,'form:'+UPLOAD).status_code==400
    app.config['MILESTONE_MAX_BYTES']=10*1024*1024
    event=db.session.get(Event,1);event.date=datetime(2020,1,1);event.end_date=datetime(2020,1,2);event.lifecycle_status='cancelled';db.session.commit()
    assert client.post(UPLOAD,data={'file':(io.BytesIO(PDF),'old-activity.pdf')}).status_code==302
    assert client.post(COMPOSE,data={'message':'Historical update','announcement_type':'event_update'}).status_code==302
    app.config['WTF_CSRF_ENABLED']=True
    assert client.post(COMPOSE,data={'message':'Blocked','announcement_type':'event_update'}).status_code==400
    assert client.post(UPLOAD,data={'file':(io.BytesIO(PDF),'blocked.pdf')}).status_code==400


@pytest.mark.parametrize('kind',['jpeg','png','webp','docx'])
def test_supported_formats_validate_at_staging_and_final_upload(app,client,actors,kind):
    sign_in(client,actors)
    if kind=='docx':content=docx().read()
    else:
        from PIL import Image
        output=io.BytesIO();Image.new('RGB',(2,2),'white').save(output,format=kind.upper());content=output.getvalue()
    key='form:'+UPLOAD
    assert stage(client,key,'evidence.'+kind,content).status_code==200
    assert client.post(UPLOAD,data={'_draft_key':key,'category':'report'}).status_code==302
    assert Milestone.query.one().filename=='evidence.'+kind
    assert FormDraft.query.count()==0
