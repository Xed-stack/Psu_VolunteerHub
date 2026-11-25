"""Coordinator Activities reference layout, scoped counts and real progress figures."""
from datetime import timedelta

from app.models import db
from app.models.event import Event, Registration, ExternalParticipant
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app, client, actors, sign_in


def _seed_reference_events(actors):
    base = local_now() + timedelta(days=2)
    events = []
    for index in range(3):
        event = Event.query.filter_by(title=f'Reference Activity {index}').first()
        if event is None:
            event = Event(title=f'Reference Activity {index}', description='Reference fixture',
                          campus_id=1, category='Education & Literacy')
            db.session.add(event)
        event.date = base + timedelta(days=index)
        event.end_date = event.date + timedelta(hours=4)
        event.slots = 50 + index
        event.target_participants = 10
        event.participant_type = 'Volunteer participants'
        event.conducting_department = f'Reference Department {index}'
        event.lifecycle_status = 'approved'
        events.append(event)
    db.session.flush()
    events[0].proposal_document = {'name': 'PSU-EXT-2026-081.pdf'}
    for index in range(3):
        person = ExternalParticipant(id_number=f'reference-{index}', name=f'Reference Person {index}')
        db.session.add(person)
        db.session.flush()
        db.session.add(Registration(event_id=events[0].id, external_participant_id=person.id, status='confirmed'))
    db.session.commit()
    return events


def test_coordinator_activities_reference_layout(app, client, actors):
    events = _seed_reference_events(actors)
    sign_in(client, actors)
    body = client.get('/workspace/activities?state=upcoming').get_data(as_text=True)
    assert 'activities-reference' in body and 'activities-tabs' in body
    assert 'Past Activities' in body and 'All Activities' in body
    assert 'Campus: Lingayen (fixed)' in body and 'name="campus_id"' not in body
    assert 'Apply Filters' in body and '>Reset</a>' in body
    assert 'Sorted by Earliest date' in body and 'View Activity' in body
    assert 'Target Volunteers 3 / 10' in body and '30% filled' in body
    assert 'Needs Attention' in body and 'Approved Proposal: PSU-EXT-2026-081.pdf' in body
    expected = Event.query.filter(Event.campus_id == 1, Event.date > local_now(),
                                  Event.lifecycle_status == 'approved').count()
    assert f'{expected}</span>' in body
    assert 'Showing 5 of' in body and 'entries</p>' in body
    assert events[2].title in body
    second = client.get('/workspace/activities?state=upcoming&page=2').get_data(as_text=True)
    assert 'Showing 2 of' in second and 'Green Campus Initiative' in second

    department = client.get('/workspace/activities?q=Reference%20Department%201').get_data(as_text=True)
    assert 'Reference Activity 1' in department and 'Reference Activity 0' not in department

    sign_in(client, actors, 'director')
    director = client.get('/workspace/activities').get_data(as_text=True)
    assert 'director-activities-desktop' in director and 'activities-reference' in director
