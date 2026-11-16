"""Landing-only footer destinations, deduplication and native navigation."""
from datetime import datetime
from unittest.mock import patch

import pytest
from tests.test_app import app,client
from tests.test_workspace_overhaul import actors,sign_in
from tests.html_helpers import parse_html


@pytest.mark.parametrize('role',['public','volunteer','coordinator','director'])
def test_footer_has_usable_public_destinations(client,actors,role):
    if role!='public':sign_in(client,actors,role)
    response=client.get('/');assert response.status_code==200
    footer=parse_html(response.get_data(as_text=True)).all('footer')[0]
    assert footer.attrs.get('class')=='landing-footer'
    assert 'Help and Process Guide' in footer.text and 'Pangasinan State University' in footer.text
    links=[link.attrs['href'] for link in footer.all('a')]
    assert links.count('/help')==1
    assert all(url in links for url in ['/opportunities','/workspace/about','/historical-activities','/help/account-access','/help/agreements','#landing-start'])
    for url in links:
        if url.startswith('#'):continue
        assert client.get(url).status_code==200,(role,url)
    assert 'landing-help' not in response.get_data(as_text=True)


def test_copyright_uses_existing_philippine_local_year(client):
    with patch('app.services.activity_workflow.local_now',return_value=datetime(2031,1,1,0,1)):
        body=client.get('/').get_data(as_text=True)
    assert '© 2031 PSU Volunteer Hub' in body


def test_back_to_top_is_native_focus_target_and_footers_are_scoped(client,actors):
    doc=parse_html(client.get('/').get_data(as_text=True))
    target=next(nav for nav in doc.all('nav') if nav.attrs.get('id')=='landing-start')
    assert target.attrs.get('tabindex')=='-1'
    for url in ['/help','/workspace/about','/auth/login']:
        assert b'class="landing-footer"' not in client.get(url).data
    sign_in(client,actors,'volunteer')
    assert b'class="role-footer"' in client.get('/help').data
    assert b'class="landing-footer"' not in client.get('/help').data
