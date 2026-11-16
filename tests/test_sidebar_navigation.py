"""Sidebar destinations, selected parents and native logout remain intact."""
import pytest
from tests.test_app import app,client,_create_user,_login_as
from tests.html_helpers import parse_html


@pytest.mark.parametrize('role,path,expected',[
    ('volunteer','/profile?section=preferences','Profile'),
    ('volunteer','/workspace/registrations','My Registrations'),
    ('coordinator','/workspace/activities/1/documents','Activities'),
    ('coordinator','/workspace/reports','Reports'),
    ('director','/workspace/catalogue/skills/new','Management'),
    ('director','/workspace/imports','Management'),
    ('director','/help','Help and Guides'),
])
def test_selected_parent_and_role_links(app,client,role,path,expected):
    _login_as(client,_create_user(app,role=role,campus_id=1))
    response=client.get(path)
    assert response.status_code==200
    sidebar=parse_html(response.text).one('aside',id='roleSidebar')
    active=[node for node in sidebar.all('a') if node.attrs.get('aria-current')=='page']
    assert len(active)==1 and active[0].one('span',**{'class':'navlink__label'}).text==expected
    links={node.attrs['href'] for node in sidebar.all('a')}
    assert '/workspace/about' in links and '/help' in links and '/workspace/drafts' in links
    assert ('/profile' in links)==(role=='volunteer')
    assert ('/workspace/management' in links)==(role=='director')
    assert '/workspace/partners' not in links or role=='coordinator'


@pytest.mark.parametrize('role',['director','coordinator','volunteer'])
def test_logout_csrf_is_preserved(app,client,role):
    _login_as(client,_create_user(app,role=role,campus_id=1))
    app.config['WTF_CSRF_ENABLED']=True
    sidebar=parse_html(client.get('/help').text).one('aside',id='roleSidebar')
    form=sidebar.one('form',action='/auth/logout')
    assert form.attrs['method']=='post'
    token=form.one('input',name='csrf_token').attrs['value']
    assert client.post('/auth/logout').status_code==400
    assert client.post('/auth/logout',data={'csrf_token':token}).status_code in (302,303)
