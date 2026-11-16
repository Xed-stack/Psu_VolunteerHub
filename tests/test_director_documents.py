"""Director document discovery reuses publication and private file permissions."""
from datetime import timedelta
from urllib.parse import quote,parse_qs,urlsplit
from pathlib import Path
import pytest
from sqlalchemy import event as sa_event
from app.models import db
from app.models.event import Event,Milestone,EventAnnouncement
from app.models.workspace import FormDraft
from app.services.activity_workflow import local_now
from tests.test_app import app,client
from tests.test_workspace_overhaul import actors,sign_in,docx
from tests.html_helpers import parse_html


@pytest.mark.parametrize('coordinator,campus',[('coordinator',1),('other',2)])
def test_coordinator_publish_director_discovers_and_downloads_proposal(app,client,actors,coordinator,campus):
    sign_in(client,actors,coordinator)
    published_before=Event.query.count()
    stream=docx();original=stream.getvalue();filename=f'Approved_Campus_{campus}.docx'
    assert client.post('/workspace/create/1',data={'proposal':(stream,filename)}).status_code==302
    assert Event.query.count()==published_before
    draft=FormDraft.query.filter_by(user_id=actors[coordinator],key='activity:new').one()
    assert draft.payload['_proposal']['name']==filename
    title=f'Published Campus {campus} Activity'
    sign_in(client,actors,'director')
    assert title not in client.get('/workspace/activities').text
    assert client.get('/workspace/drafts/activity:new').status_code==403
    sign_in(client,actors,coordinator)
    start=local_now()+timedelta(days=10)
    details=dict(title=title,description='Authored description',category=Event.query.first().category,
        date=start.isoformat(timespec='minutes'),end_date=(start+timedelta(hours=2)).isoformat(timespec='minutes'),slots='20',cancellation_days='2')
    assert client.post('/workspace/create/2',data=details).status_code==302
    assert client.post('/workspace/create/3',data={'participant_type':'Students'}).status_code==302
    assert client.post('/workspace/create/4').status_code==302
    activity=Event.query.filter_by(title=title).one()
    assert activity.campus_id==campus and activity.lifecycle_status=='approved'
    sign_in(client,actors,'director')
    overview=client.get(f'/workspace/activities/{activity.id}?return_to=/workspace/activities?state=upcoming')
    assert overview.status_code==200
    tree=parse_html(overview.text).one('main',id='main-content')
    assert len([h for h in tree.all('h2') if h.text=='Approved Proposal'])==1
    assert overview.text.index('director-proposal-heading')<overview.text.index('Activity Overview</h2>')
    destination=next(a.attrs['href'] for a in tree.all('a') if a.text=='View All Documents')
    assert parse_qs(urlsplit(destination).query)['return_to']==['/workspace/activities?state=upcoming']
    response=client.get(destination)
    assert response.status_code==200 and filename in response.text
    file=client.get(f'/workspace/activities/{activity.id}/proposal')
    assert file.status_code==200 and file.data==original and filename in file.headers['Content-Disposition']
    assert client.get(f'/workspace/reports/activities/{activity.id}').status_code==200


def test_director_lists_supporting_files_without_querying_private_history(app,client,actors,monkeypatch):
    sign_in(client,actors,'director')
    for i in range(27):db.session.add(Milestone(event_id=1,filename=f'Evidence {i}.pdf',upload_path='milestones/test.pdf'))
    db.session.add(EventAnnouncement(event_id=1,announcement_type='event_update',message='Coordinator-only announcement'))
    db.session.add(FormDraft(user_id=actors['director'],campus_id=1,key='form:/workspace/activities/1/documents',payload={'message':['Old private draft']}))
    db.session.commit()
    def forbidden(*args):raise AssertionError('Director must not inspect draft resumes')
    monkeypatch.setattr('app.services.activity_documents.legacy_resumes',forbidden)
    statements=[]
    def record(conn,cursor,statement,*args):statements.append(statement.lower())
    sa_event.listen(db.engine,'before_cursor_execute',record)
    try:response=client.get('/workspace/activities/1/documents?view=announcements&resume=private&page=2')
    finally:sa_event.remove(db.engine,'before_cursor_execute',record)
    assert response.status_code==200
    tree=parse_html(response.text).one('main',id='main-content')
    assert len(tree.all('article'))==2
    for text in ['Coordinator-only announcement','Old private draft','Upload Evidence','Compose Announcement','Resume Saved','Announcement History']:
        assert text not in tree.text
    assert not tree.all('form') and 'Read-only access' in tree.text
    assert not any('from event_announcements' in sql or 'from form_drafts' in sql for sql in statements)
    nav=tree.one('nav',**{'aria-label':'Activity Workspace'})
    assert nav.one('a',**{'aria-current':'page'}).text=='Documents'
    help_link=next(a.attrs['href'] for a in tree.all('a') if a.text=='Document Help')
    assert client.get(help_link).status_code==200


@pytest.mark.parametrize('path',[
    '/workspace/activities/1/documents/upload','/workspace/activities/1/announcements/new',
    '/events/1/milestones','/coordinator/events/1/announcements',
])
def test_director_forged_writes_remain_denied(client,actors,path):
    sign_in(client,actors,'director')
    response=client.post(path,data={'message':'Denied','announcement_type':'event_update'})
    assert response.status_code==403
    assert Milestone.query.count()==0 and EventAnnouncement.query.count()==0


def test_missing_unavailable_files_and_coordinator_scope(app,client,actors):
    sign_in(client,actors,'director')
    assert 'No approved proposal file is attached' in client.get('/workspace/activities/1/documents').text
    assert client.get('/workspace/activities/1/proposal').status_code==404
    activity=db.session.get(Event,1);activity.proposal_document={'name':'Unavailable.pdf','path':'missing.pdf'}
    record=Milestone(event_id=1,filename='Legacy.pdf',upload_path='uploads/retired.pdf');db.session.add(record);db.session.commit()
    assert client.get('/workspace/activities/1/proposal').status_code==404
    assert client.get(f'/milestones/{record.id}/download').status_code==410
    sign_in(client,actors,'other');assert client.get('/workspace/activities/1/documents').status_code==404
    sign_in(client,actors,'volunteer');assert client.get('/workspace/activities/1/documents').status_code==403
    sign_in(client,actors,'coordinator')
    response=client.get('/workspace/activities/1/documents')
    assert response.status_code==200 and 'Upload Evidence' in response.text and 'Announcements' in response.text
