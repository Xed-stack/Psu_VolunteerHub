"""Queue reminders and roster refinements preserve recorded evidence."""
from datetime import timedelta
import pytest
from werkzeug.datastructures import MultiDict
from app.models import db
from app.models.event import Event, Registration, Attendance, ExternalParticipant
from app.models.user import User
from app.models.notification import Notification
from app.models.finding_review import FindingReview, FindingReviewEvent
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_attendance_rosters_ui import ongoing
from tests.test_finding_reviews import active, post, review_case
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html, form_values


def reminder_form(client):
    page=parse_html(client.get('/workspace/follow-up?period=all&review_group=attendance').text)
    return next(form for form in page.all('form') if any(b.text=='Remind Coordinator' for b in form.all('button')))


@pytest.mark.parametrize('enabled',[False,True])
def test_queue_dates_category_and_single_reminder(client,app,actors,ongoing,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director')
    response=client.get('/workspace/follow-up?period=all&review_group=attendance')
    assert response.status_code==200
    page=parse_html(response.text)
    assert len(page.all('select',name='review_group'))==1
    assert not page.all('select',name='finding_type')
    assert 'Advanced Filters in Reports' not in page.text
    assert 'Start:' in page.text and 'End:' in page.text and 'Philippine time' in page.text
    event=db.session.get(Event,1)
    assert event.date.strftime('%d %b %Y, %I:%M %p') in page.text
    assert event.end_date.strftime('%d %b %Y, %I:%M %p') in page.text
    form=reminder_form(client)
    assert len(form.all('button'))==1
    assert client.get('/workspace/overview?period=all').status_code==200
    assert 'Advanced Filters in Reports' in client.get('/workspace/overview?period=all').text
    if enabled:
        assert not page.all('a',**{'class':'btn btn--outline'}) or 'Review Ongoing Activity' not in page.text


@pytest.mark.parametrize('enabled',[False,True])
def test_quick_reminder_native_post_and_duplicate(client,app,actors,ongoing,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director')
    for attempt in range(2):
        form=reminder_form(client)
        response=client.post(form.attrs['action'],data=MultiDict(form_values(form)))
        assert response.status_code==302
        assert response.location=='/workspace/follow-up?period=all&review_group=attendance'
        assert Notification.query.filter_by(notification_type='campus_guidance').count()==1
    if enabled:assert FindingReviewEvent.query.filter_by(action='follow_up_sent').count()==1
    sign_in(client,actors)
    page=client.get('/notifications').text
    assert 'guidance message is unavailable' not in page
    assert '/workspace/activities/1' in page


def test_quick_reminder_preserves_assessment_and_recommendation(client,app,actors,ongoing):
    app.config['FINDING_REVIEWS_ENABLED']=True
    sign_in(client,actors,'director')
    item=active(client,app,'record_attendance')[0]
    assert post(client,item,'save',assessment='Keep this authored assessment.').status_code==302
    form=reminder_form(client)
    assert client.post(form.attrs['action'],data=MultiDict(form_values(form))).status_code==302
    row=FindingReview.query.one()
    assert row.assessment=='Keep this authored assessment.' and row.recommendation=='review_future_targets'
    assert row.status=='follow_up_sent'


@pytest.mark.parametrize('enabled',[False,True])
def test_stale_reminder_at_end_never_sends(client,app,actors,ongoing,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director');form=reminder_form(client)
    db.session.get(Event,1).end_date=local_now();db.session.commit()
    response=client.post(form.attrs['action'],data=MultiDict(form_values(form)))
    assert response.status_code in (302,400,409)
    assert Notification.query.filter_by(notification_type='campus_guidance').count()==0
    assert FindingReviewEvent.query.count()==0


@pytest.mark.parametrize('enabled',[False,True])
def test_missing_coordinator_and_invalid_category(client,app,actors,ongoing,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    db.session.get(User,actors['coordinator'])._is_active=False;db.session.commit()
    sign_in(client,actors,'director')
    page=parse_html(client.get('/workspace/follow-up?period=all&review_group=attendance').text)
    button=next(b for b in page.all('button') if b.text=='Remind Coordinator')
    assert 'disabled' in button.attrs
    assert 'No active Coordinator' in client.get('/workspace/follow-up?period=all').text
    assert client.get('/workspace/follow-up?review_group=bad').status_code==400
    assert client.get('/workspace/follow-up?review_group=attendance&review_group=annual').status_code==400


def test_review_history_schedule_uses_saved_snapshot(client,app,review_case):
    event,_=review_case;start,end=event.date,event.end_date
    item=active(client,app)[0];assert post(client,item).status_code==302
    occurrence=FindingReviewEvent.query.filter_by(action='closed').one()
    event.date+=timedelta(days=4);event.end_date+=timedelta(days=4);db.session.commit()
    html=client.get('/workspace/follow-up?period=all&review_tab=reviewed').text
    detail=client.get(f'/workspace/finding-reviews/{item["key"]}?occurrence={occurrence.id}').text
    for body in [html,detail]:
        assert start.strftime('%d %b %Y, %I:%M %p') in body
        assert end.strftime('%d %b %Y, %I:%M %p') in body


@pytest.mark.parametrize('external',[False,True])
def test_attendance_choices_bulk_and_legacy_preservation(client,actors,ongoing,external):
    sign_in(client,actors)
    reg=db.session.get(Registration,ongoing)
    if external:
        person=ExternalParticipant(name='Legacy community attendee',id_number='EXT-LEGACY')
        db.session.add(person);db.session.flush()
        reg=Registration(event_id=1,external_participant_id=person.id,status='confirmed')
        db.session.add(reg);db.session.flush()
    path='/workspace/activities/1/external' if external else '/attendance?event_id=1'
    data={'action':'attendance'} if external else {'event_id':'1'}
    data.update(registration_id=str(reg.id),status='excused')
    assert client.post(path,data=data).status_code==400
    db.session.add(Attendance(registration_id=reg.id,event_id=1,user_id=reg.user_id,status='excused'));db.session.commit()
    page=parse_html(client.get(path).text)
    select=page.one('select',name='status')
    assert [o.attrs['value'] for o in select.all('option')]==['','present','absent']
    assert 'Excused (Existing Record)' in select.text and 'Attended' in select.text
    button=page.one('button',**{'data-attendance-bulk':'present'})
    assert button.text=='All Attended' and 'hidden' in button.attrs
    assert client.post(path,data=data).status_code==302
    db.session.expire_all();assert db.session.get(Registration,reg.id).attendance_record.status=='excused'
    assert client.post(path,data=dict(data,status='')).status_code==302
    db.session.expire_all();assert db.session.get(Registration,reg.id).attendance_record.status=='excused'
    data['status']='present';assert client.post(path,data=data).status_code==302
    db.session.expire_all();assert db.session.get(Registration,reg.id).attendance_record.status=='present'
    assert client.post(path,data=dict(data,status='excused')).status_code==400


def test_recognition_entry_is_report_card(client,actors):
    sign_in(client,actors,'director')
    page=parse_html(client.get('/workspace/reports').text)
    nav=page.one('nav',**{'aria-label':'Annual Recognition Reports'})
    link=nav.one('a')
    assert link.one('h3').text=='Outstanding Recognition' and link.one('span').text=='Open Report'
    assert link.attrs['href'].startswith('/workspace/recognition')


@pytest.mark.parametrize('enabled',[False,True])
def test_category_filters_before_pagination_and_replaces_legacy_scope(client,app,actors,ongoing,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director')
    event=db.session.get(Event,1)
    for i in range(27):
        another=Event(title=f'Attendance queue fixture {i}',date=event.date,end_date=event.end_date,
                      campus_id=1,lifecycle_status='approved',description='Synthetic')
        db.session.add(another);db.session.flush()
        db.session.add(Registration(event_id=another.id,user_id=actors['volunteer'],status='confirmed'))
    db.session.commit()
    response,context=screen(client,app,'/workspace/follow-up?period=all&review_group=attendance&page=2')
    assert context['total']==28 and len(context['items'])==3
    page=parse_html(client.get('/workspace/follow-up?period=all&finding_type=record_attendance').text)
    assert 'Clear Finding Type' in page.text
    category=next(f for f in page.all('form') if f.all('select',name='review_group'))
    assert 'finding_type' not in form_values(category) and 'page' not in form_values(category)
    assert FindingReview.query.count()==FindingReviewEvent.query.count()==0


@pytest.mark.parametrize('enabled',[False,True])
def test_reminder_final_timing_check_rolls_back(client,app,actors,ongoing,monkeypatch,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director');form=reminder_form(client)
    calls=[]
    def open_then_ended(event,now=None):
        calls.append(event.id)
        return len(calls)==1
    monkeypatch.setattr('app.services.activity_workflow.attendance_open',open_then_ended)
    response=client.post(form.attrs['action'],data=MultiDict(form_values(form)))
    assert response.status_code in (302,400)
    assert len(calls)==2
    assert Notification.query.filter_by(notification_type='campus_guidance').count()==0
    assert FindingReview.query.count()==FindingReviewEvent.query.count()==0


@pytest.mark.parametrize('enabled',[False,True])
def test_reminder_csrf_and_role_checks(client,app,actors,ongoing,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director');form=reminder_form(client)
    app.config['WTF_CSRF_ENABLED']=True
    data=MultiDict(form_values(form));data.pop('csrf_token',None)
    assert client.post(form.attrs['action'],data=data).status_code==400
    app.config['WTF_CSRF_ENABLED']=False
    sign_in(client,actors)
    assert client.post(form.attrs['action'],data=data).status_code==403
    assert Notification.query.filter_by(notification_type='campus_guidance').count()==0


@pytest.mark.parametrize('value',['//outside.invalid','/workspace/follow-up\\evil','/workspace/reports','https://outside.invalid'])
def test_queue_return_rejects_unrelated_destinations(client,app,value):
    from app.ui import follow_up_return
    with app.test_request_context():assert follow_up_return(value) is None
