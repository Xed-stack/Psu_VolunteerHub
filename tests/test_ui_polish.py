"""Search, navigation context, guidance preferences, and safe presentation."""
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from app.models import db
from app.models.event import Event, Registration
from app.models.user import User
from app.models.workspace import PartnerAgency
from app.services.activity_workflow import local_now
from app.ui import back_url, highlight, query_url
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.html_helpers import parse_html


def test_safe_literal_highlighting_and_query_state(app):
    assert str(highlight('<img onerror=alert(1)>100%_Done', '%_')) == '&lt;img onerror=alert(1)&gt;100<mark>%_</mark>Done'
    assert str(highlight('Campus CAMPUS', 'campus')) == '<mark>Campus</mark> <mark>CAMPUS</mark>'
    with app.test_request_context('/opportunities?campus=1&campus=2&search=tree&page=4&category=Environment'):
        query = parse_qs(urlsplit(query_url(campus=['2'])).query)
        assert query == {'campus':['2'], 'search':['tree'], 'category':['Environment']}
        query = parse_qs(urlsplit(query_url(remove='search')).query)
        assert query['campus'] == ['1', '2'] and 'page' not in query and 'search' not in query
    for unsafe in ('https://example.org', '//example.org', '/\\example.org', '/\n/example.org'):
        with app.test_request_context('/workspace/activities/1',query_string={'return_to':unsafe}):
            assert back_url('workspace.activities') == '/workspace/activities'


def test_literal_search_order_scope_and_back_context(client, actors):
    sign_in(client, actors)
    rows = Event.query.order_by(Event.id).limit(3).all()
    for index, row in enumerate(rows):
        row.title = 'Literal 100%_Match ' + str(index)
        row.date = local_now() + timedelta(days=3-index)
        row.end_date = row.date + timedelta(hours=2)
        row.campus_id = 1 if index < 2 else 2
    db.session.commit()
    response = client.get('/workspace/activities',query_string={'q':'100%_Match','state':'upcoming','category':rows[0].category})
    assert response.status_code == 200
    assert b'<mark>100%_Match</mark>' in response.data
    assert b'Literal 100<mark>%_</mark>' not in response.data
    assert b'Literal 100%_Match 2' not in response.data
    response = client.get('/workspace/activities?q=100%25_Match')
    document = parse_html(response.get_data(as_text=True))
    links = [a for heading in document.all('h2') for a in heading.all('a') if 'Literal 100%_Match' in a.text]
    assert [a.text for a in links] == ['Literal 100%_Match 1','Literal 100%_Match 0']
    detail = client.get(links[0].attrs['href'])
    back = [a for a in parse_html(detail.get_data(as_text=True)).all('a') if a.text.endswith('Back to Activities')][0]
    assert parse_qs(urlsplit(back.attrs['href']).query)['q'] == ['100%_Match']
    assert b'No Matching Activities' in client.get('/workspace/activities?q=unfindable%25_').data
    # SQL wildcard characters only match records containing those characters.
    assert b'Youth Coding Mentor' not in client.get('/opportunities?search=%25_').data


def test_partner_and_registration_search_are_private(client, actors):
    sign_in(client, actors)
    db.session.add_all([PartnerAgency(name='100%_Agency',contact_name='A',campus_id=1),
                        PartnerAgency(name='100%_Private agency',contact_name='B',campus_id=2)])
    event = Event.query.first()
    event.title = 'Volunteer 100%_activity'
    db.session.add(Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed'))
    db.session.add(Registration(event_id=event.id,user_id=actors['director'],status='completed'))
    db.session.commit()
    response = client.get('/workspace/partners?q=%25_')
    assert b'Private agency' not in response.data and b'<mark>%_</mark>Agency' in response.data
    sign_in(client, actors, 'volunteer')
    response = client.get('/workspace/registrations?q=%25_&status=confirmed')
    assert b'<mark>%_</mark>activity' in response.data
    link = [a for a in parse_html(response.get_data(as_text=True)).all('a') if a.text == event.title][0]
    detail = client.get(link.attrs['href'])
    back = [a for a in parse_html(detail.get_data(as_text=True)).all('a') if a.text.endswith('Back to Registrations')][0]
    assert parse_qs(urlsplit(back.attrs['href']).query)['status'] == ['confirmed']
    assert b'No Matching Registrations' in client.get('/workspace/registrations?status=completed').data


def test_departments_are_scoped_and_exports_match(client, actors):
    sign_in(client, actors)
    rows = Event.query.order_by(Event.id).limit(2).all()
    for index, row in enumerate(rows):
        row.campus_id = index+1
        row.conducting_department = 'Visible department' if index == 0 else 'Other campus department'
        row.date = local_now()
    db.session.commit()
    document = parse_html(client.get('/workspace/reports/results').get_data(as_text=True))
    options = document.one('select',name='department').text
    assert 'Visible department' in options and 'Other campus department' not in options
    query = '?department=Visible+department'
    csv = client.get('/workspace/reports/export/csv'+query)
    assert csv.status_code == 200 and b'Visible department' in csv.data and b'Other campus department' not in csv.data
    response = client.get('/workspace/reports/results?campus_id=2')
    assert b'Other campus department' not in response.data
    assert b'Remove Campus:' not in response.data


def test_guidance_preferences_and_error_pages(client, actors):
    for role, path in [('coordinator','/workspace/overview'),('director','/workspace/overview'),('volunteer','/volunteer_dash')]:
        sign_in(client, actors, role)
        response = client.get(path)
        assert b'data-tour-first-use="true"' in response.data
        assert b'Show Dashboard Guide' in response.data
        assert client.post('/guide/dismiss',headers={'Accept':'application/json'}).status_code == 200
        saved = db.session.get(User,actors[role]).first_use_guide_dismissed_at
        assert saved is not None
        assert b'data-tour-first-use="false"' in client.get(path).data
        assert b'data-tour-replay="true"' in client.get(path+'?tour=1').data
        assert db.session.get(User,actors[role]).first_use_guide_dismissed_at == saved
    assert client.get('/missing-page').status_code == 404


def test_all_templates_compile(app):
    for name in app.jinja_env.list_templates():
        app.jinja_env.get_template(name)
