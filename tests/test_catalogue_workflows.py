"""Archived catalogue choices cannot silently change current or new assignments."""
from datetime import timedelta
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_activity_forms import choices, details
from app.models import db
from app.models.user import Skill, Interest, User
from app.models.event import ActivityCategory, Event
from app.models.workspace import FormDraft
from app.services.activity_workflow import local_now
from app.recommendation.engine import bootstrap_from_event


def test_activity_edit_retains_archived_but_rejects_new_archived(client,actors):
    sign_in(client,actors)
    skills,sdgs=choices();event=Event.query.first()
    event.date=local_now()+timedelta(days=12);event.end_date=event.date+timedelta(hours=2)
    event.lifecycle_status='approved';event.required_skills_rel=[skills[0]];event.sdgs=sdgs
    skills[0].is_active=False;skills[1].is_active=False
    ActivityCategory.query.filter_by(name=event.category).one().is_active=False
    db.session.commit()
    path=f'/coordinator/events/{event.id}/edit'
    assert b'(Archived)' in client.get(path).data
    form=details(event,sdgs);form['required_skills']=[skills[0].name]
    assert client.post(path,data=form).status_code==302
    assert not event.required_skills_rel[0].is_active
    form['required_skills']=[skills[1].name]
    assert client.post(path,data=form).status_code==200
    assert event.required_skills_rel==[skills[0]]


def test_new_activity_stale_draft_is_explained_and_not_published(client,actors):
    sign_in(client,actors);skills,sdgs=choices();event=Event.query.first()
    category=ActivityCategory.query.filter_by(name=event.category).one();category.is_active=False
    skills[0].is_active=False
    payload=details(event,sdgs);payload['required_skills']=[str(skills[0].id)];payload['_proposal']='private-fixture.docx'
    db.session.add(FormDraft(user_id=actors['coordinator'],campus_id=1,key='activity:new',payload=payload));db.session.commit()
    assert b'archived or unavailable' in client.get('/workspace/create/2').data
    response=client.post('/workspace/create/4')
    assert response.status_code==200 and b'Choose an available category.' in response.data
    assert not Event.query.filter_by(title='Simplified activity').first()


def test_profile_retains_owned_archive_rejects_other_archive_and_bootstrap(client,actors):
    interest=Interest(name='QA Profile Interest');owned=Skill(name='QA Owned Archived',is_active=False,interests=[interest]);other=Skill(name='QA Other Archived',is_active=False)
    user=db.session.get(User,actors['volunteer']);user.interests=[interest];user.skills=[owned]
    db.session.add_all([interest,owned,other]);db.session.commit();sign_in(client,actors,'volunteer')
    assert b'QA Owned Archived (Archived)' in client.get('/profile?section=preferences').data
    assert client.post('/profile',data={'skills':[str(owned.id)],'interests':[str(interest.id)]}).status_code==302
    assert client.post('/profile',data={'skills':[str(other.id)],'interests':[str(interest.id)]}).status_code==422
    assert user.skills==[owned]
    empty=db.session.get(User,actors['coordinator']);event=Event.query.first();event.required_skills_rel=[owned];db.session.commit()
    bootstrap_from_event(empty,event)
    assert not empty.skills
