"""Director cards and entry routing agree with the existing review queue."""
from datetime import timedelta
from urllib.parse import urlsplit, parse_qs
import pytest
from app.models import db
from app.models.event import Event, Registration, Attendance
from app.models.finding_review import FindingReview, FindingReviewEvent
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_ui_reimagining import screen
from tests.test_finding_reviews import active, post


@pytest.fixture
def activities_case(app, actors):
    now=local_now()
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=None
    events={}
    for name,start,end,campus in [
        ('Ready',now+timedelta(days=2),now+timedelta(days=3),1),
        ('Missing End',now+timedelta(days=1),None,1),
        ('Ended',now-timedelta(days=3),now-timedelta(days=2),1),
        ('Other',now+timedelta(days=4),now+timedelta(days=5),2),
    ]:
        event=Event(title='Director Cards '+name,description='Synthetic',date=start,end_date=end,
                    campus_id=campus,lifecycle_status='approved',target_participants=10,
                    category='Education & Literacy',conducting_department='Director Fixture')
        db.session.add(event);db.session.flush();events[name]=event
    db.session.add(Registration(event_id=events['Ended'].id,user_id=actors['volunteer'],status='confirmed'))
    db.session.commit()
    return events


@pytest.mark.parametrize('enabled',[False,True])
def test_director_cards_and_entry_match_queue(client,app,actors,activities_case,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled
    sign_in(client,actors,'director')
    events=activities_case
    before=(Attendance.query.count(),FindingReview.query.count(),FindingReviewEvent.query.count())
    response,data=screen(client,app,'/workspace/activities?state=all&q=Director+Cards')
    cards={card['event'].id:card for card in data['cards']}
    assert cards[events['Ready'].id]['finding_count']==0
    assert cards[events['Missing End'].id]['finding_count']==1
    assert cards[events['Ended'].id]['finding_count']==1
    assert not any(card['low'] for card in data['cards'])
    assert 'Review Findings' in response.text and 'Create Activity' not in response.text
    for name in ('Missing End','Ended'):
        opened=client.get(cards[events[name].id]['open_url'])
        assert opened.status_code==302 and urlsplit(opened.location).path=='/workspace/follow-up'
        params=parse_qs(urlsplit(opened.location).query)
        assert params['event_id']==[str(events[name].id)] and params['period']==['all'] and params['page']==['1']
        queue,context=screen(client,app,opened.location)
        assert queue.status_code==200 and context['total']==cards[events[name].id]['finding_count']
        assert all((item['snapshot']['event_id'] if enabled else item['event'].id)==events[name].id for item in context['items'])
    opened=client.get(cards[events['Ready'].id]['open_url'])
    assert urlsplit(opened.location).path==f"/workspace/activities/{events['Ready'].id}"
    assert client.get(opened.location).status_code==200
    assert client.get(f"/workspace/activities/{events['Missing End'].id}").status_code==200
    assert before==(Attendance.query.count(),FindingReview.query.count(),FindingReviewEvent.query.count())
    sign_in(client,actors)
    assert client.get(cards[events['Ready'].id]['open_url']).status_code==403
    assert client.get(f"/workspace/activities/{events['Other'].id}").status_code==404


def test_closed_review_opens_details_changed_evidence_reopens(client,app,actors,activities_case):
    app.config['FINDING_REVIEWS_ENABLED']=True
    sign_in(client,actors,'director')
    event=activities_case['Missing End']
    item=active(client,app,code='schedule_limit',event_id=event.id)[0]
    assert post(client,item).status_code==302
    url=f'/workspace/activities/{event.id}/open'
    assert urlsplit(client.get(url).location).path==f'/workspace/activities/{event.id}'
    event.target_participants=20;db.session.commit()
    assert urlsplit(client.get(url).location).path=='/workspace/follow-up'
    assert FindingReview.query.one().status=='closed'
    assert client.get('/workspace/activities/999999/open').status_code==404
    assert not client.get(url+'?return_to=https://example.invalid').location.startswith('https:')


def test_director_counts_filters_pagination_and_return_context(client,app,actors,activities_case):
    sign_in(client,actors,'director')
    now=local_now()
    for index in range(6):
        db.session.add(Event(title=f'Director Cards More {index}',description='Synthetic',campus_id=1,
            date=now+timedelta(days=6+index),end_date=now+timedelta(days=7+index),
            lifecycle_status='approved',category='Education & Literacy'))
    db.session.commit()
    _,data=screen(client,app,'/workspace/activities?state=upcoming&q=Director+Cards&campus_id=1')
    assert data['pagination'].per_page==5 and len(data['cards'])==5
    assert data['counts']['upcoming']==8 and data['counts']['past']==1
    assert data['counts']['all']==9 and data['campus_name']=='Lingayen'
    starts=[card['event'].date for card in data['cards']]
    assert starts==sorted(starts)
    _,page=screen(client,app,'/workspace/activities?state=upcoming&q=Director+Cards&campus_id=1&page=2')
    assert len(page['cards'])==3
    _,filtered=screen(client,app,'/workspace/activities?state=all&q=Director+Fixture&campus_id=2&category=Education+%26+Literacy')
    assert len(filtered['cards'])==1 and filtered['cards'][0]['event'].campus_id==2
    _,empty=screen(client,app,'/workspace/activities?q=Nothing+Matches')
    assert not empty['cards']
    return_to='/workspace/activities?state=all&q=Director+Cards&campus_id=1&page=2'
    target=client.get(f"/workspace/activities/{activities_case['Ready'].id}/open",query_string={'return_to':return_to})
    assert parse_qs(urlsplit(target.location).query)['return_to']==[return_to]
    assert client.get('/workspace/activities?campus_id=bad').status_code==400
    assert client.get('/workspace/activities?campus_id=999999').status_code==400


def test_unresolved_cleared_finding_stays_in_queue_and_entry_rechecks(client,app,actors,activities_case):
    app.config['FINDING_REVIEWS_ENABLED']=True
    sign_in(client,actors,'director')
    event=activities_case['Missing End']
    item=active(client,app,code='schedule_limit',event_id=event.id)[0]
    assert post(client,item,action='save').status_code==302
    event.end_date=event.date+timedelta(hours=2);db.session.commit()
    opened=client.get(f'/workspace/activities/{event.id}/open')
    assert urlsplit(opened.location).path=='/workspace/follow-up'
    _,queue=screen(client,app,opened.location)
    assert queue['total']==1 and not queue['items'][0]['detected']
    ready=activities_case['Ready']
    _,listing=screen(client,app,'/workspace/activities?q=Director+Cards+Ready')
    assert listing['cards'][0]['finding_count']==0
    ready.end_date=None;db.session.commit()
    assert urlsplit(client.get(listing['cards'][0]['open_url']).location).path=='/workspace/follow-up'
