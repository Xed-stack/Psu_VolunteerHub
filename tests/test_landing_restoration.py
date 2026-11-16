"""Restored landing composition retains current copy, scope and activity journeys."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from app.models import db
from app.models.event import Event, HistoricalActivity
from app.services.activity_workflow import local_now
from tests.test_app import app,client
from tests.test_workspace_overhaul import actors,sign_in
from tests.html_helpers import parse_html


COPY = [
    'Your campus.','Your community.','Your contribution.',
    'Find an activity that connects your interests with the people and places you can help.',
    'Explore Activities','Become a Volunteer',
    'Open to PSU students, faculty, staff, and external volunteers.',
    'Service starts with people working together.',
    'Choose Your Cause','Select interests and skills to discover activities that match.',
    'Find Your Activity','Review the schedule, campus, requirements, and agreement before joining.',
    'Follow Your Commitment','Keep upcoming activities in your calendar and track verified participation.',
    'Upcoming Campus Activities','Open an activity for the complete details.','View All Activities',
    'Service in Action','Past approved activities with a recorded end time.',
    'PSU’s Documented Service','Historical source records are reported separately from live participation and annual-plan evidence.',
    'Review Source Records','Historical Activity Records','Known Reported Participations',
    'Aggregate participations are not unique volunteers.','records have no recorded participation count.',
    'About Us','Help and Process Guide',
]


def test_current_copy_restored_layout_and_no_legacy_actions(client):
    text=client.get('/').get_data(as_text=True)
    for phrase in COPY:assert phrase in text,phrase
    doc=parse_html(text)
    assert len(doc.all('main'))==1
    assert 'data-hero-carousel' in text and text.count('data-hero-slide')==5
    assert 'data-hero-pause' in text and 'data-hero-dot="4"' in text
    assert 'public-home.js' in text and 'landing-hero__scrim' in text
    assert 'Serve with purpose.' not in text and 'Opportunities' not in text
    assert '/opportunities/register/' not in text and 'Join Now' not in text
    assert '/styles/public.css' not in text and '/styles/app.css' in text
    images=[image for image in doc.all('img') if 'data-hero-slide' in image.attrs]
    assert len(images)==5 and images[0].attrs.get('fetchpriority')=='high'
    assert images[0].attrs.get('src') and all('src' not in image.attrs and image.attrs.get('data-src') for image in images[1:])
    assert all(image.attrs.get('width') and image.attrs.get('height') and image.attrs.get('alt') for image in images)


@pytest.mark.parametrize('role',['volunteer','coordinator','director'])
def test_signed_in_landing_keeps_dashboard_and_detail_navigation(client,actors,role):
    sign_in(client,actors,role);text=client.get('/').get_data(as_text=True)
    assert '>Dashboard</a>' in text and '>Become a Volunteer</a>' not in text
    assert 'sticky-header.js' not in text and 'role-topbar' not in text
    assert '/opportunities/register/' not in text


@pytest.mark.parametrize('start,end,status,featured,completed',[
    (1,2,'approved',True,False),(-1,1,'approved',False,False),(-2,-1,'approved',False,True),
    (-2,0,'approved',False,True),(-1,None,'approved',False,False),(1,None,'approved',True,False),
    (1,2,'cancelled',False,False),(-2,-1,'cancelled',False,False),
])
def test_current_activity_eligibility_is_preserved(client,app,start,end,status,featured,completed):
    now=local_now().replace(microsecond=0)
    db.session.add(Event(title='Authored Boundary Title',description='Authored Boundary Description',date=now+timedelta(hours=start),
        end_date=now+timedelta(hours=end) if end is not None else None,lifecycle_status=status,campus_id=1,slots=20))
    db.session.commit()
    with patch('app.services.activity_workflow.local_now',return_value=now):text=client.get('/').get_data(as_text=True)
    events=text.split('id="upcoming-title"',1)[1].split('class="landing-impact"',1)[0]
    stories=text.split('id="stories-title"',1)[1]
    assert ('Authored Boundary Title' in events)==featured
    assert ('Authored Boundary Title' in stories)==completed


def test_unknown_history_and_empty_states_remain_explicit(client,app):
    Event.query.delete();HistoricalActivity.query.delete();db.session.commit()
    text=client.get('/').get_data(as_text=True)
    assert 'No upcoming activities are available yet. Check back for new campus activities.' in text
    assert 'Completed activity highlights will appear when recorded schedules confirm delivery.' in text
    assert '>Not recorded</dd>' in text
    assert 'data-carousel-controls' not in text


def test_latest_completed_stories_and_cover_fallback(client,app):
    Event.query.delete();now=local_now()
    for n in range(4):
        db.session.add(Event(title=f'Authored Finish {n}',description='Authored description',date=now-timedelta(days=n+2),
            end_date=now-timedelta(days=n+1),lifecycle_status='approved',campus_id=1,slots=10,
            cover_image_path='assets/FB_IMG_1788789005999.jpg' if n==0 else None))
    db.session.commit();text=client.get('/').get_data(as_text=True)
    assert all(f'Authored Finish {n}' in text for n in range(3)) and 'Authored Finish 3' not in text
    assert 'landing-event-art' in text and 'loading="lazy"' in text
    assert 'View Activity Details' in text and 'data-open-event' not in text


def test_historical_counts_remain_separate_and_unknown_is_not_zero(client,app):
    HistoricalActivity.query.delete()
    for key,count in [('known',12),('unknown',None)]:
        db.session.add(HistoricalActivity(source_key=key,source_document='Authored archive',source_page=1,source_row=1,
            unit_name='Lingayen',title='Authored historical activity',volunteer_count=count,year_conducted=2024))
    db.session.commit();text=client.get('/').get_data(as_text=True)
    assert 'Historical Activity Records</dt><dd>2</dd>' in text
    assert 'Known Reported Participations</dt><dd>12</dd>' in text
    assert '1 records have no recorded participation count.' in text
    assert 'Aggregate participations are not unique volunteers.' in text
