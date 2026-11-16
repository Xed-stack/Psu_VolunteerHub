"""Help content visibility, safe search, links, and read-only role guidance."""
from copy import deepcopy
from urllib.parse import quote

import pytest
from sqlalchemy import event
from app.help_center import TOPICS
from app.models import db
from app.models.user import User
from tests.test_app import app,client
from tests.test_workspace_overhaul import actors,sign_in
from tests.html_helpers import parse_html


@pytest.mark.parametrize('role',['public','volunteer','coordinator','director'])
def test_help_topics_and_shell_follow_role(client,actors,role):
    if role!='public':sign_in(client,actors,role)
    response=client.get('/help');assert response.status_code==200
    text=response.get_data(as_text=True)
    assert text.count('<main ')==1
    assert ('class="role-topbar"' in text)==(role!='public')
    for item in TOPICS:
        article=client.get('/help/'+item['slug'])
        assert article.status_code==(200 if role in item['audience'] else 404),(role,item['slug'])
        assert ('href="/help/'+item['slug']+'"' in text)==(role in item['audience'])
    if role!='public':
        links=parse_html(text).all('a')
        help_link=next(link for link in links if link.attrs.get('href')=='/help' and 'navlink' in link.attrs.get('class',''))
        assert help_link.attrs.get('aria-current')=='page'
        assert 'Show Dashboard Guide' in text
    else:
        assert 'Show Dashboard Guide' not in text


def test_help_search_literal_escaped_and_back_context(client,actors):
    sign_in(client,actors,'coordinator')
    found=client.get('/help?q=attendance').get_data(as_text=True)
    assert '<mark>Attendance</mark>' in found
    assert '/help/attendance?q=attendance' in found
    article=client.get('/help/attendance?q=attendance').get_data(as_text=True)
    assert 'href="/help?q=attendance"' in article
    for query in ['%','_','<script>alert(1)</script>']:
        text=client.get('/help?q='+quote(query,safe='')).get_data(as_text=True)
        assert '<script>alert(1)</script>' not in text
        if query in ['%','_']:
            # Those characters match the literal navigation examples, not every topic.
            assert 'Creating an Approved Activity</h3>' not in text
    no_results=client.get('/help?q=unfindable-literal-text').data
    assert b'No Matching Help Topics' in no_results and b'Browse All Help' in no_results
    assert b'Reset Search' in no_results


@pytest.mark.parametrize('role',['public','volunteer','coordinator','director'])
def test_search_never_reveals_other_role_content(client,actors,role):
    if role!='public':sign_in(client,actors,role)
    text=client.get('/help?q=import').get_data(as_text=True)
    if role!='director':assert 'href="/help/imports' not in text and 'href="/workspace/imports' not in text
    else:assert '/help/imports' in text


def test_help_reads_do_not_write_or_dismiss_guide(client,app,actors):
    sign_in(client,actors,'director');before=deepcopy(TOPICS);writes=[]
    user=db.session.get(User,actors['director']);dismissed=user.first_use_guide_dismissed_at
    def capture(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().split(' ',1)[0].upper() in ('INSERT','UPDATE','DELETE'):writes.append(statement)
    event.listen(db.engine,'before_cursor_execute',capture)
    try:
        for url in ['/help','/help/reports','/help/notifications','/help?q=draft']:
            assert client.get(url).status_code==200
    finally:event.remove(db.engine,'before_cursor_execute',capture)
    assert not writes and TOPICS==before
    assert user.first_use_guide_dismissed_at==dismissed
    assert '/workspace/overview?tour=1' in client.get('/help').get_data(as_text=True)


@pytest.mark.parametrize('role',['public','volunteer','coordinator','director'])
def test_all_help_action_and_related_urls_resolve(client,app,actors,role):
    if role!='public':sign_in(client,actors,role)
    for item in TOPICS:
        if role not in item['audience']:continue
        doc=parse_html(client.get('/help/'+item['slug']).get_data(as_text=True))
        for link in doc.all('a'):
            href=link.attrs.get('href','')
            if not href.startswith('/') or href.startswith('//'):continue
            path=href.split('?',1)[0]
            app.url_map.bind('').match(path,method='GET')
            if path.startswith('/help/'):
                assert client.get(href).status_code==200


def test_contextual_help_targets_authorized_articles(client,actors):
    sign_in(client,actors)
    assert b'/help/create-activity' in client.get('/workspace/create/1').data
    assert b'/help/annual-plans' in client.get('/workspace/overview').data
    sign_in(client,actors,'volunteer')
    assert b'/help/recommendations' in client.get('/volunteer_dash').data
    assert client.get('/help/attendance').status_code==404


def test_unknown_article_and_methods(client):
    assert client.get('/help/not-a-topic').status_code==404
    assert client.post('/help').status_code==405
    assert client.post('/help/getting-started').status_code==405
