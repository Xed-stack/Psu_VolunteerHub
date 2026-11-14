"""Activity journeys retain context, evidence states and authorization."""
from datetime import timedelta
from html import unescape
import re
from urllib.parse import urlencode, urlsplit, parse_qs

from app.models import db
from app.models.event import Event, Registration
from app.routes.events import _agreement_for
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app, client, actors, sign_in


def upcoming():
    event = Event.query.first()
    event.date = local_now() + timedelta(days=10)
    event.end_date = event.date + timedelta(hours=2)
    event.cancellation_deadline = event.date - timedelta(days=1)
    event.lifecycle_status = 'approved'
    event.slots = 20
    db.session.commit()
    return event


def test_registered_detail_and_withdrawal_keep_filtered_origin(client, actors):
    sign_in(client, actors, 'volunteer')
    event = upcoming()
    reg = Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed')
    db.session.add(reg); db.session.commit()
    origin = '/opportunities?search=tree&campus=1&campus=2&page=3'
    query = '?' + urlencode({'return_to':origin})
    html = unescape(client.get(f'/opportunities/{event.id}'+query).text)
    assert f'/workspace/registrations/{reg.id}?' in html
    assert 'View Your Registration' in html
    assert 'href="'+origin+'"' in html
    path = f'/registrations/{reg.id}/cancel'+query
    html = unescape(client.get(path).text)
    assert 'Back to Registration' in html and f'/workspace/registrations/{reg.id}?' in html
    response = client.post(path)
    assert urlsplit(response.location).path == f'/workspace/registrations/{reg.id}'
    assert parse_qs(urlsplit(response.location).query)['return_to'] == [origin]
    assert reg.status == 'cancelled'
    html = unescape(client.get(response.location).text)
    assert 'href="'+origin+'"' in html


def test_join_lands_on_registration_and_fresh_get_excludes_consent(client, actors):
    sign_in(client, actors, 'volunteer')
    event = upcoming(); event.nda_required=True; event.nda_text='Authored NDA'; event.nda_version='private-version'
    db.session.commit()
    origin='/opportunities?search=100%25_&campus=1&campus=2'
    query='?'+urlencode({'return_to':origin,'campus':[1,2]},doseq=True)
    url=f'/opportunities/register/{event.id}'+query
    assert client.post(url,data={'accept_agreement':'yes'}).status_code == 400
    fresh=client.get(url).text
    assert not re.search(r'<input\b[^>]*\schecked(?:\s|>|=)',fresh) and 'data-no-draft' in fresh
    assert 'private-version' not in fresh
    response=client.post(url,data={'accept_agreement':'yes','accept_nda':'yes'})
    reg=Registration.query.filter_by(event_id=event.id,user_id=actors['volunteer']).one()
    assert urlsplit(response.location).path == f'/workspace/registrations/{reg.id}'
    assert parse_qs(urlsplit(response.location).query)['campus']==['1','2']
    assert reg.policy_accepted_at and reg.nda_accepted_at


def test_cancelled_detail_unlimited_capacity_and_safe_back(client, actors):
    sign_in(client, actors, 'volunteer')
    event=upcoming();event.slots=0;db.session.commit()
    html=client.get(f'/opportunities/{event.id}?return_to=https://example.org').text
    assert 'No capacity limit' in html and 'href="https://example.org"' not in html
    event.lifecycle_status='cancelled';event.cancellation_reason='Authored closure reason';db.session.commit()
    html=client.get(f'/opportunities/{event.id}').text
    assert 'Authored closure reason' in html and 'This activity has started.' not in html
    assert 'Review and Join</a>' not in html


def test_workspace_primary_action_and_registration_isolation(client, actors):
    sign_in(client, actors)
    event=upcoming()
    html=client.get(f'/workspace/activities/{event.id}').text
    assert 'Edit Activity Details</a>' in html and 'Record Attendance</a>' not in html
    event.date=local_now()-timedelta(minutes=30);event.end_date=local_now()+timedelta(hours=1);db.session.commit()
    assert 'Record Attendance</a>' in client.get(f'/workspace/activities/{event.id}').text
    event.end_date=local_now()-timedelta(minutes=1);db.session.commit()
    html=client.get(f'/workspace/activities/{event.id}').text
    assert 'View Activity Report</a>' in html and 'Record Attendance</a>' not in html
    event.end_date=None;db.session.commit()
    assert 'Attendance is read-only' in client.get(f'/workspace/activities/{event.id}').text
    sign_in(client,actors,'other')
    assert client.get(f'/workspace/activities/{event.id}').status_code==404
    reg=Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed');db.session.add(reg);db.session.commit()
    assert client.get(f'/workspace/registrations/{reg.id}').status_code==403


def test_default_agreement_and_authored_policy(client, actors):
    event=upcoming();event.participation_agreement_text='Authored agreement text.';db.session.commit()
    assert _agreement_for(event)['body']=='Authored agreement text.'
    event.participation_agreement_text=None
    from app.models.policy import ParticipationAgreementRevision
    ParticipationAgreementRevision.query.delete();db.session.commit()
    assert 'withdraw before the withdrawal deadline' in _agreement_for(event)['body']
