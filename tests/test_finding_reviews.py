"""Review actions preserve source facts, history and authorization."""
from datetime import timedelta
from urllib.parse import urlencode
import pytest
from sqlalchemy import create_engine,inspect
from app.models import db
from app.models.event import Event,Registration,Attendance
from app.models.workspace import ActivityProposal
from app.models.notification import Notification
from app.models.finding_review import FindingReview,FindingReviewEvent
from app.services.activity_workflow import local_now
from app.finding_review_migration import migrate_finding_reviews
from tests.test_workspace_overhaul import app,client,actors,sign_in
from tests.test_ui_reimagining import screen


@pytest.fixture
def review_case(app,client,actors):
    app.config['FINDING_REVIEWS_ENABLED']=True
    now=local_now()
    event=Event(title='Review fixture',description='Synthetic review',date=now-timedelta(days=2),
        end_date=now-timedelta(days=1),campus_id=1,lifecycle_status='approved',target_participants=20)
    db.session.add(event);db.session.flush()
    registration=Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed')
    db.session.add(registration);db.session.commit()
    sign_in(client,actors,'director')
    return event,registration


def active(client,app,code='pending_attendance',**params):
    _,data=screen(client,app,'/workspace/follow-up?'+urlencode(dict({'period':'all','finding_type':code},**params)))
    return data['items']


def post(client,item,action='close',**changes):
    values=dict(source=item['token'],revision=item['revision'],version=str(item['version']),action=action,
        assessment='The historical evidence was reviewed carefully.',recommendation='review_future_targets',closure_reason='historical_outcome_reviewed')
    values.update(changes)
    return client.post('/workspace/finding-reviews/'+item['key'],data=values)


def test_get_refresh_creates_no_review_and_filters_keep_identity(client,app,review_case):
    first=active(client,app)[0]
    second=active(client,app,sex='female',year=str(local_now().year-1))[0]
    assert first['key']==second['key'] and first['fingerprint']==second['fingerprint']
    assert FindingReview.query.count()==FindingReviewEvent.query.count()==0
    assert client.get('/workspace/finding-reviews/'+first['key']+'?source='+first['token']).status_code==200


def test_close_preserves_facts_and_history_permissions(client,app,actors,review_case):
    event,registration=review_case
    item=active(client,app)[0]
    before=(event.target_participants,event.end_date,registration.status,Attendance.query.count())
    assert post(client,item).status_code==302
    assert not active(client,app)
    row=FindingReview.query.one();closed=FindingReviewEvent.query.filter_by(action='closed').one()
    assert row.status=='closed' and before==(event.target_participants,event.end_date,registration.status,Attendance.query.count())
    url=f'/workspace/finding-reviews/{row.finding_key}?occurrence={closed.id}'
    sign_in(client,actors)
    assert client.get(url).status_code==200
    assert client.get('/workspace/finding-reviews/'+row.finding_key).status_code==403
    assert client.post(url,data={}).status_code==403
    sign_in(client,actors,'other');assert client.get(url).status_code==404
    sign_in(client,actors,'volunteer');assert client.get(url).status_code==403


def test_changed_evidence_reappears_without_writes_and_keeps_previous_assessment(client,app,actors,review_case):
    event,_=review_case;item=active(client,app)[0]
    assert post(client,item).status_code==302
    db.session.add(Registration(event_id=event.id,user_id=actors['coordinator'],status='confirmed'));db.session.commit()
    changed=active(client,app)[0]
    assert changed['changed'] and changed['assessment']=='' and changed['status']=='needs_review'
    assert FindingReview.query.one().status=='closed'
    assert post(client,changed,assessment='New evidence was assessed separately.').status_code==302
    closes=FindingReviewEvent.query.filter_by(action='closed').order_by(FindingReviewEvent.id).all()
    assert len(closes)==2 and closes[0].content['assessment']!=closes[1].content['assessment']
    assert FindingReviewEvent.query.filter_by(action='evidence_changed').count()==1


def test_cleared_open_finding_stays_for_assessment(client,app,review_case):
    event,registration=review_case;item=active(client,app)[0]
    assert post(client,item,'save').status_code==302
    db.session.add(Attendance(event_id=event.id,registration_id=registration.id,status='present'));db.session.commit()
    item=active(client,app)[0]
    assert not item['detected'] and 'No longer detected' in item['snapshot']['evidence']
    assert item['snapshot']['facts']['metrics']['present']==1
    assert post(client,item,closure_reason='evidence_completed').status_code==302
    assert not active(client,app)


def test_stale_submit_retains_note_and_no_duplicate_history(client,app,review_case):
    item=active(client,app)[0]
    assert post(client,item,'save').status_code==302
    response=post(client,item,assessment='Keep this unsaved assessment for comparison.')
    assert response.status_code==409 and 'Keep this unsaved assessment' in response.text
    assert FindingReviewEvent.query.count()==1
    fresh=active(client,app)[0]
    assert post(client,fresh).status_code==302
    assert post(client,fresh).status_code==409
    assert FindingReviewEvent.query.filter_by(action='closed').count()==1


def test_material_change_between_get_and_post_conflicts(client,app,review_case):
    event,_=review_case;item=active(client,app)[0]
    event.target_participants=25;db.session.commit()
    assert post(client,item).status_code==409
    assert FindingReview.query.count()==0


@pytest.mark.parametrize('changes',[{'assessment':'short'},{'closure_reason':'invented'},{'recommendation':'invented'},{'assessment':'x'*4001}])
def test_invalid_decisions_do_not_write(client,app,review_case,changes):
    assert post(client,active(client,app)[0],**changes).status_code==400
    assert FindingReview.query.count()==FindingReviewEvent.query.count()==0


def test_only_actionable_followups_send_and_decode(client,app,actors,review_case):
    event,_=review_case
    assert post(client,active(client,app)[0],'follow_up').status_code==400
    event.date=local_now()-timedelta(hours=1);event.end_date=local_now()+timedelta(hours=1);db.session.commit()
    item=active(client,app,'record_attendance')[0]
    assert post(client,item,'follow_up').status_code==302
    assert FindingReview.query.one().status=='follow_up_sent'
    notes=Notification.query.filter_by(notification_type='campus_guidance').all();assert len(notes)==1
    item=active(client,app,'record_attendance')[0]
    assert post(client,item,'follow_up').status_code==302
    assert Notification.query.filter_by(notification_type='campus_guidance').count()==1
    assert FindingReviewEvent.query.count()==1
    sign_in(client,actors)
    response=client.get('/notifications')
    assert response.status_code==200 and 'Campus Review Follow-Up' in response.text and 'unavailable' not in response.text


def test_failed_notification_transaction_rolls_back(client,app,review_case,monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    event,_=review_case;event.end_date=local_now()+timedelta(hours=1);db.session.commit()
    item=active(client,app,'record_attendance')[0]
    def fail():raise SQLAlchemyError('Synthetic commit failure')
    monkeypatch.setattr(db.session,'commit',fail)
    response=post(client,item,'follow_up')
    assert response.status_code==503 and 'historical evidence was reviewed' in response.text
    assert FindingReview.query.count()==FindingReviewEvent.query.count()==0
    assert Notification.query.filter_by(notification_type='campus_guidance').count()==0


def test_reopen_requires_reason_and_preserves_closed_snapshot(client,app,review_case):
    item=active(client,app)[0];assert post(client,item).status_code==302
    from app.services.finding_reviews import resolve
    # Resolve through a fresh request context to validate the closed form's token.
    _,context=screen(client,app,'/workspace/finding-reviews/'+item['key'])
    closed=context['item']
    assert post(client,closed,'reopen',assessment='').status_code==400
    assert post(client,closed,'reopen',assessment='Reopened for a documented second assessment.').status_code==302
    assert len(active(client,app))==1
    assert FindingReviewEvent.query.filter_by(action='closed').one().content['assessment']=='The historical evidence was reviewed carefully.'


def test_feature_disabled_and_missing_storage_fall_back(client,app,review_case):
    app.config['FINDING_REVIEWS_ENABLED']=False
    response=client.get('/workspace/overview');assert 'Findings to Review' in response.text and 'data-review-chart' not in response.text
    app.config['FINDING_REVIEWS_ENABLED']=True
    FindingReviewEvent.__table__.drop(db.engine)
    response=client.get('/workspace/follow-up');assert response.status_code==200 and 'Generated findings are shown' in response.text


def test_explicit_migration_dry_run_repeatability():
    import app.models.user,app.models.event
    engine=create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        for table in ('users','campuses','events'):connection.exec_driver_sql(f'CREATE TABLE {table} (id INTEGER PRIMARY KEY)')
    with pytest.raises(ValueError):migrate_finding_reviews(engine,'wrong')
    assert len(migrate_finding_reviews(engine,':memory:',True))==2
    assert 'finding_reviews' not in inspect(engine).get_table_names()
    assert len(migrate_finding_reviews(engine,':memory:'))==2
    assert migrate_finding_reviews(engine,':memory:')==[]


def test_planning_identity_uses_period_boundaries_and_annual_identity_uses_year(client,app,review_case):
    Event.query.filter_by(campus_id=9).update({'lifecycle_status':'cancelled'});db.session.commit()
    year=local_now().year
    item=active(client,app,'no_activities',campus_id='9',year=str(year),period='annual')[0]
    detail=client.get('/workspace/finding-reviews/'+item['key'],query_string={'source':item['token']})
    assert 'View Campus Calendar' in detail.text
    assert post(client,item).status_code==302
    assert not active(client,app,'no_activities',campus_id='9',year=str(year),period='custom',start_date=f'{year}-01-01',end_date=f'{year}-12-31')
    annual=active(client,app,'no_targets',campus_id='9',year=str(year),period='all')[0]
    assert post(client,annual).status_code==302
    assert not active(client,app,'no_targets',campus_id='9',year=str(year),period='quarterly',segment='1')
    assert active(client,app,'no_targets',campus_id='9',year=str(year+1),period='all')[0]['key']!=annual['key']


def test_review_history_is_database_paginated(client,app,actors,review_case):
    item=active(client,app)[0];assert post(client,item).status_code==302
    first=FindingReviewEvent.query.filter_by(action='closed').one()
    for i in range(27):
        db.session.add(FindingReviewEvent(review_id=first.review_id,campus_id=1,actor_id=actors['director'],actor_name='Director',
            action='closed',content=dict(first.content,assessment=f'Historical assessment {i}')))
    db.session.commit()
    _,data=screen(client,app,'/workspace/follow-up?period=all&review_tab=reviewed&page=2')
    assert data['total']==28 and len(data['items'])==3 and data['pages']==2
    _,detail=screen(client,app,'/workspace/finding-reviews/'+item['key']+'?history_page=2')
    assert len(detail['history'])==3 and detail['history_pages']==2


def test_missing_source_retains_review_and_snapshot(client,app,review_case):
    event,registration=review_case;item=active(client,app)[0];assert post(client,item,'save').status_code==302
    Registration.query.filter_by(event_id=event.id).delete();Event.query.filter_by(id=event.id).delete();db.session.commit()
    remaining=active(client,app)[0]
    assert not remaining['detected'] and remaining['snapshot']['facts']['source_unavailable']
    assert post(client,remaining).status_code==302
    assert FindingReviewEvent.query.filter_by(action='closed').one().content['snapshot']['event_title']=='Review fixture'


def test_csrf_and_non_director_posts_are_rejected(client,app,actors,review_case):
    item=active(client,app)[0]
    app.config['WTF_CSRF_ENABLED']=True
    assert post(client,item).status_code==400
    app.config['WTF_CSRF_ENABLED']=False
    sign_in(client,actors)
    assert post(client,item).status_code==403
    assert FindingReview.query.count()==0


def test_aggregation_adds_no_query_per_finding(client,app,review_case):
    from tests.test_system_performance import query_count
    with query_count(app) as small:active(client,app)
    event,registration=review_case
    for i in range(27):
        another=Event(title=f'More review {i}',description='Synthetic',date=event.date,end_date=event.end_date,campus_id=1,lifecycle_status='approved')
        db.session.add(another);db.session.flush()
        db.session.add(Registration(event_id=another.id,user_id=registration.user_id,status='confirmed'))
    db.session.commit()
    with query_count(app) as large:rows=active(client,app)
    assert len(rows)==25 and len(large)<=len(small)+2,(len(small),len(large))


def test_ineligible_or_cosmetic_changes_do_not_reopen(client,app,actors,review_case):
    event,registration=review_case;item=active(client,app)[0];assert post(client,item).status_code==302
    db.session.add(Registration(event_id=event.id,user_id=actors['coordinator'],status='cancelled'))
    event.title='Cosmetic activity rename';registration.status='completed';db.session.commit()
    remaining=active(client,app)
    assert not remaining, {k:(v,remaining[0]['snapshot']['facts'].get(k)) for k,v in item['snapshot']['facts'].items() if v!=remaining[0]['snapshot']['facts'].get(k)}


def test_review_snapshot_remains_with_original_campus_after_transfer(client,app,actors,review_case):
    event,_=review_case;item=active(client,app)[0];assert post(client,item).status_code==302
    closed=FindingReviewEvent.query.filter_by(action='closed').one()
    event.campus_id=2;db.session.commit()
    sign_in(client,actors)
    _,history=screen(client,app,'/workspace/follow-up?period=all&review_tab=reviewed')
    assert history['total']==1
    response=client.get(f'/workspace/finding-reviews/{item["key"]}?occurrence={closed.id}')
    assert response.status_code==200 and 'View Activity Evidence' not in response.text
    sign_in(client,actors,'other')
    assert client.get(f'/workspace/finding-reviews/{item["key"]}?occurrence={closed.id}').status_code==404
