"""Inbox state, safe actions, UTC presentation and preserved draft boundaries."""
from datetime import datetime, timedelta, timezone
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from app.models import db
from app.models.notification import Notification
from app.models.workspace import FormDraft
from app.ui import utc_record_time
from tests.test_app import app, client, _create_user, _login_as
from tests.html_helpers import parse_html


def add_notes(uid, count=1, read=False):
    rows = [Notification(user_id=uid, title=f'Authored <Title> {i}', message='Private message 100%_',
                         is_read=read, created_at=datetime(2026,11,16,17,0)-timedelta(minutes=i))
            for i in range(count)]
    db.session.add_all(rows)
    db.session.commit()
    return [row.id for row in rows]


@pytest.mark.parametrize('role',['director','coordinator','volunteer'])
def test_tabs_ownership_counts_time_and_action_forms(app,client,role):
    uid=_create_user(app,role=role,campus_id=1)
    other=_create_user(app,email='foreign@example.org',campus_id=2)
    own=add_notes(uid,2)
    read=add_notes(uid,1,True)
    foreign=add_notes(other,2)
    _login_as(client,uid)
    response=client.get('/notifications?view=unread')
    assert response.status_code==200
    tree=parse_html(response.text)
    assert len(tree.all('article'))==2
    assert {n.attrs['id'] for n in tree.one('main',id='main-content').all('h2')}=={f'notification-{i}' for i in own}
    assert '2 unread notifications' in tree.text
    assert '&lt;Title&gt;' in response.text
    for time in tree.all('time'):
        assert time.attrs['datetime'].endswith('+08:00')
        assert '17 Nov 2026' in time.text and 'Philippine Time' in time.text
        assert datetime.fromisoformat(time.attrs['datetime']).hour in (0,1)
    forms=[f for f in tree.all('form') if f.attrs.get('action','').startswith('/notifications/')]
    assert len(forms)==3
    assert all('data-no-draft' in f.attrs and f.all('input',name='csrf_token') for f in forms)
    page=client.get('/notifications').text
    assert len(parse_html(page).all('article'))==3
    assert db.session.get(Notification,own[0]).is_read is False
    assert db.session.get(Notification,foreign[0]).is_read is False
    assert read


@pytest.mark.parametrize('value',['','bad','https://outside.example','ALL'])
def test_invalid_view_defaults_to_all(app,client,value):
    uid=_create_user(app,campus_id=1)
    add_notes(uid,read=True)
    _login_as(client,uid)
    tree=parse_html(client.get('/notifications',query_string={'view':value}).text)
    nav=tree.one('nav',**{'aria-label':'Notification Views'})
    assert nav.one('a',**{'aria-current':'page'}).text=='All'
    assert len(tree.all('article'))==1


def test_read_keeps_view_page_and_clamps_last_page(app,client):
    uid=_create_user(app,campus_id=1)
    ids=add_notes(uid,26)
    _login_as(client,uid)
    tree=parse_html(client.get('/notifications?view=unread&page=2').text)
    assert len(tree.all('article'))==1
    response=client.post(f'/notifications/{ids[-1]}/read?view=unread&page=2')
    assert parse_qs(urlsplit(response.location).query)=={'view':['unread'],'page':['1']}
    assert db.session.get(Notification,ids[-1]).is_read
    response=client.post(f'/notifications/{ids[0]}/read?view=all&page=2')
    assert parse_qs(urlsplit(response.location).query)=={'view':['all'],'page':['2']}
    assert len(parse_html(client.get('/notifications?view=unread&page=999').text).all('article'))==24
    assert 'view=unread' in client.get('/notifications?view=unread').text


def test_mark_all_affects_owner_and_all_pages_only(app,client):
    uid=_create_user(app,campus_id=1)
    other=_create_user(app,email='other@example.org',campus_id=2)
    add_notes(uid,27)
    foreign=add_notes(other)
    _login_as(client,uid)
    response=client.post('/notifications/read-all?view=unread&page=2',follow_redirects=True)
    assert response.status_code==200 and 'You’re All Caught Up' in response.text
    assert Notification.query.filter_by(user_id=uid,is_read=False).count()==0
    assert not db.session.get(Notification,foreign[0]).is_read
    assert 'No Notifications Yet' not in response.text


def test_empty_states_and_csrf(app,client):
    uid=_create_user(app,campus_id=1)
    ids=add_notes(uid)
    _login_as(client,uid)
    app.config['WTF_CSRF_ENABLED']=True
    tree=parse_html(client.get('/notifications').text)
    token=tree.one('meta',name='csrf-token').attrs['content']
    assert client.post(f'/notifications/{ids[0]}/read').status_code==400
    assert client.post('/notifications/read-all').status_code==400
    assert client.post(f'/notifications/{ids[0]}/read',data={'csrf_token':token}).status_code==302
    Notification.query.filter_by(user_id=uid).delete();db.session.commit()
    assert 'No Notifications Yet' in client.get('/notifications').text
    assert 'No Saved Drafts' in client.get('/workspace/drafts').text


def test_foreign_read_and_login_boundary(app,client):
    assert client.get('/notifications?view=unread').status_code==302
    assert client.get('/workspace/drafts').status_code==302
    uid=_create_user(app,campus_id=1)
    other=_create_user(app,email='foreign@example.org',campus_id=2)
    nid=add_notes(other)[0]
    _login_as(client,uid)
    from flask import g
    g.pop('_login_user',None)
    client.post(f'/notifications/{nid}/read?view=unread')
    assert not db.session.get(Notification,nid).is_read
    assert client.post('/notifications/999999/read').status_code==404


@pytest.mark.parametrize('role,campus,has_link',[
    ('coordinator',1,True),('coordinator',2,False),('volunteer',1,False),('director',1,False),
])
def test_guidance_destinations_keep_authorized_scope(app,client,role,campus,has_link):
    uid=_create_user(app,role=role,campus_id=campus)
    payload={'version':1,'text':'Review campus obligations.',
             'identity':{'campus_id':1,'goal_year':2026,'rule':'remaining_goals'}}
    db.session.add(Notification(user_id=uid,title='Campus evidence',message=json.dumps(payload),notification_type='campus_guidance'))
    db.session.commit()
    _login_as(client,uid)
    tree=parse_html(client.get('/notifications').text).one('main',id='main-content')
    links=[a for a in tree.all('a') if a.text.startswith('Review Campus Records')]
    assert bool(links)==has_link
    if has_link:
        query=parse_qs(urlsplit(links[0].attrs['href']).query)
        assert query['campus']==['1'] and query['year']==['2026']
    else:
        assert 'guidance message is unavailable' in tree.text


def test_draft_labels_order_scope_resume_and_upload_discard(app,client,tmp_path):
    uid=_create_user(app,role='coordinator',campus_id=1)
    other=_create_user(app,email='other@example.org',role='coordinator',campus_id=1)
    app.config['PRIVATE_UPLOAD_FOLDER']=str(tmp_path)
    folder=tmp_path/'draft-uploads';folder.mkdir()
    file=folder/'private.pdf';file.write_bytes(b'private sample')
    db.session.add_all([
        FormDraft(user_id=uid,campus_id=1,key='activity:new',payload={'title':['Authored title'], '_files':{'document':{'path':'private.pdf','name':'private.pdf'}}},updated_at=datetime(2026,11,16,17)),
        FormDraft(user_id=uid,campus_id=1,key='form:/workspace/partners',payload={},updated_at=datetime(2026,11,15,17)),
        FormDraft(user_id=uid,campus_id=2,key='form:/settings',payload={}),
        FormDraft(user_id=other,campus_id=1,key='activity:new',payload={}),
    ]);db.session.commit()
    _login_as(client,uid)
    tree=parse_html(client.get('/workspace/drafts').text).one('main',id='main-content')
    assert [n.text for n in tree.all('h2')]==['New Activity','New Partner Agency']
    assert len(tree.all('article'))==2
    assert '01:00 AM' in tree.all('time')[0].text
    hrefs={a.attrs['href'] for a in tree.all('a')}
    assert '/workspace/create/1' in hrefs
    assert any('/workspace/partners/new?resume=' in h for h in hrefs)
    assert len(tree.all('p',role='status'))==2
    assert 'JavaScript is required to discard' in tree.text
    assert file.exists()
    assert client.delete('/workspace/drafts/activity:new').status_code==204
    assert not file.exists()
    assert FormDraft.query.filter_by(user_id=other).count()==1
    assert FormDraft.query.filter_by(user_id=uid,campus_id=2).count()==1


@pytest.mark.parametrize('value,expected',[
    (datetime(2026,11,16,17),'2026-11-17T01:00:00+08:00'),
    (datetime(2026,11,16,17,tzinfo=timezone.utc),'2026-11-17T01:00:00+08:00'),
    (datetime(2026,11,16,17,tzinfo=timezone(timedelta(hours=8))),'2026-11-16T17:00:00+08:00'),
])
def test_utc_record_time(value,expected):
    assert utc_record_time(value).isoformat()==expected
    assert utc_record_time(None) is None
