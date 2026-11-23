"""Campus achievement and grouped findings preserve Coordinator scope and work."""
from datetime import date, datetime
from types import SimpleNamespace as NS
from urllib.parse import parse_qs, urlsplit

import pytest

from app.models import db
from app.models.annual_plan import AnnualTarget, AnnualActivityMapping
from app.models.event import Campus, Event
from app.report_demo import seed_aop_commitments
from app.services.aop_goals import progress
from app.services.staff_overview import campus_aop_achievement
from tests.html_helpers import parse_html, form_values, form_with_control
from tests.test_system_performance import query_count
from tests.test_ui_reimagining import screen
from tests.test_workspace_overhaul import app, client, actors, sign_in


def campus_fixture(completed):
    events = []
    for campus, count in ((1, completed), (2, 5)):
        for index in range(count):
            event = Event(title=f'Synthetic Campus {campus} AOP {index}', description='Synthetic',
                          campus_id=campus, date=datetime(2025, 6, 1, 8),
                          end_date=datetime(2025, 6, 1, 9), lifecycle_status='approved')
            db.session.add(event)
            events.append(event)
    db.session.flush()
    seed_aop_commitments(2025, Campus.query.order_by(Campus.id).all(), events)
    goal = AnnualTarget.query.filter_by(workflow_kind='director_goal').one()
    children = AnnualTarget.query.filter_by(workflow_kind='campus_commitment').all()
    for child in children:
        child.target_value = 10 if child.campus_id == 1 else 20
    child = next(child for child in children if child.campus_id == 1)
    for status, start, end in (
        ('cancelled', datetime(2025, 6, 1), datetime(2025, 6, 2)),
        ('approved', datetime(2024, 12, 31), datetime(2025, 1, 1)),
        ('approved', datetime(2025, 6, 1), None),
    ):
        event = Event(title='Synthetic Ineligible Campus AOP', description='Synthetic', campus_id=1,
                      date=start, end_date=end, lifecycle_status=status)
        db.session.add(event)
        db.session.flush()
        db.session.add(AnnualActivityMapping(target_id=child.id, event_id=event.id))
    db.session.commit()
    return goal, child, [event for event in events if event.campus_id == 1]


def test_duplicate_mapping_is_one_credit_per_goal_not_one_per_record():
    goal = NS(id=1, target_value=100, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
    event = NS(id=1, campus_id=1, date=datetime(2025, 6, 1), end_date=datetime(2025, 6, 2),
               lifecycle_status='approved')
    mapping = NS(event_id=1, event=event)
    child = NS(director_target_id=1, campus_id=1, target_value=2, activity_mappings=[mapping, mapping])
    assessed = progress(goal, [child], campus_id=1)
    result = campus_aop_achievement(dict(goals=dict(rows=[
        dict(target=assessed['target'], actual=assessed['completed'])])))
    assert result['completed'] == 1 and result['target'] == result['committed'] == 2
    assert result['rate'] == 50


@pytest.mark.parametrize('completed,rate', [(0, 0), (1, 10), (10, 100), (13, 130)])
def test_campus_percentage_uses_submitted_target_and_existing_eligibility(client, app, actors, completed, rate):
    goal, child, events = campus_fixture(completed)
    goal.target_value = 100
    db.session.commit()
    sign_in(client, actors)
    response, context = screen(client, app, '/workspace/overview?year=2025&period=annual')
    result = context['campus_achievement']
    assert result['target'] == result['committed'] == 10
    assert result['completed'] == completed and result['rate'] == rate
    assert result['exceeded'] == max(completed - 10, 0)
    assert goal.target_value == 100 and child.target_value == 10
    page = parse_html(response.text)
    hero = page.one('section', **{'class': 'director-achievement'})
    assert f'{rate}% Campus AOP Goal Achievement Rate' in hero.text
    assert [tile.one('h3').text for tile in page.all('article', **{'class': 'director-achievement-metric'})] == [
        'Conducted Activities', 'Verified Attendees', 'Campus Commitments']
    assert response.text.index('class="staff-scope"') < response.text.index('class="director-achievement"')
    assert response.text.index('id="agenda-title"') < response.text.index('id="review-card-title"')
    for removed in ('class="metric-tile"', 'data-month-chart', 'data-sex-chart', 'staff-footer-links', 'class="staff-annual"'):
        assert removed not in response.text
    assert 'Pending attendance recording' not in hero.text
    with query_count(app) as queries:
        assert campus_aop_achievement(context) == result
    assert len(queries) == 0
    for query in ('&period=quarterly&segment=1&sex=female', '&activity_name=NoMatch',
                  '&campus_id=2&campus=2&campus_mode=exclude'):
        _, scoped = screen(client, app, '/workspace/overview?year=2025' + query)
        assert scoped['campus_id'] == 1 and scoped['campus_achievement'] == result
        assert all(row['event'].campus_id == 1 for row in scoped['rows'])
    assert client.get('/annual-goals?year=2025&campus=1').status_code == 200


def test_multiple_goals_count_each_linked_activity_once_per_goal(client, app, actors):
    goal, child, events = campus_fixture(3)
    second = AnnualTarget(source_key='synthetic-second-director-goal', indicator_id=goal.indicator_id,
                          target_value=50, workflow_kind='director_goal', start_date=goal.start_date,
                          end_date=goal.end_date, deadline=goal.deadline)
    db.session.add(second)
    db.session.flush()
    commitment = AnnualTarget(source_key='synthetic-second-campus-commitment', indicator_id=goal.indicator_id,
                              campus_id=1, director_target_id=second.id, workflow_kind='campus_commitment',
                              target_value=2)
    db.session.add(commitment)
    db.session.flush()
    for event in events:
        db.session.add(AnnualActivityMapping(target_id=commitment.id, event_id=event.id))
    db.session.commit()
    sign_in(client, actors)
    _, context = screen(client, app, '/workspace/overview?year=2025')
    assert context['campus_achievement']['completed'] == 6
    assert context['campus_achievement']['target'] == 12
    assert context['campus_achievement']['rate'] == 50
    _, other_year = screen(client, app, '/workspace/overview?year=2024')
    assert other_year['campus_achievement']['rate'] is None
    assert other_year['campus_achievement']['target'] == other_year['campus_achievement']['completed'] == 0


@pytest.mark.parametrize('reviews_enabled', [False, True])
def test_coordinator_findings_match_campus_queue_without_director_decisions(client, app, actors, reviews_enabled):
    app.config['FINDING_REVIEWS_ENABLED'] = reviews_enabled
    sign_in(client, actors)
    response, context = screen(client, app, '/workspace/overview?period=all&campus_id=2&sex=female&page=3')
    page = parse_html(response.text)
    card = page.one('section', **{'data-tour-id': 'follow-up', 'class': 'staff-section review-card',
                                 'data-review-persisted': 'false', 'aria-labelledby': 'review-card-title'})
    assert f"{context['finding_total']} Findings to Review" in card.text
    assert context['review_summary'] is None
    assert 'Active Reviews' not in card.text and 'Reviewed History' not in card.text
    links = card.one('ul', **{'class': 'review-card-groups'}).all('a')
    assert len(links) == 4
    assert sum(group['total'] for group in context['attention_summary']['groups']) == context['finding_total']
    next_group = next(group for group in context['attention_summary']['groups'] if group['total'])
    next_link = card.one('p', **{'class': 'director-review-next'}).one('a')
    assert parse_qs(urlsplit(next_link.attrs['href']).query)['review_group'] == [next_group['key']]
    for link, group in zip(links, context['attention_summary']['groups']):
        query = parse_qs(urlsplit(link.attrs['href']).query)
        assert query['review_group'] == [group['key']] and query['page'] == ['1']
        assert query['sex'] == ['female'] and 'review_tab' not in query
        _, queue = screen(client, app, link.attrs['href'])
        assert queue['total'] == group['total']
        assert queue['campus_id'] == 1 and all(item['campus'].id == 1 for item in queue['items'])
    empty, empty_context = screen(client, app, '/workspace/overview?year=1900&category=NoMatch')
    assert empty_context['campus_achievement']['rate'] is None
    assert empty_context['finding_total'] == 0
    empty_card = parse_html(empty.text).one('section', **{'data-tour-id': 'follow-up', 'class': 'staff-section review-card',
                                                        'data-review-persisted': 'false', 'aria-labelledby': 'review-card-title'})
    assert '0 Findings' in empty_card.text and 'No generated findings' in empty_card.text
    assert any(link.text == 'View Queue' for link in empty_card.all('a'))


def test_scope_form_and_creation_link_preserve_work(client, app, actors):
    sign_in(client, actors)
    key = '/workspace/drafts/activity:new'
    assert client.put(key, json={'title': ['Retained Coordinator Draft']}).status_code == 200
    response = client.get('/workspace/overview?year=2025&period=quarterly&segment=2&sex=female')
    page = parse_html(response.text)
    values = form_values(form_with_control(page, 'period'))
    assert values['year'] == ['2025'] and values['segment'] == ['2'] and values['sex'] == ['female']
    assert 'campus_id' not in values
    create = next(link for link in page.all('a') if link.text == 'Create Activity')
    assert client.get(create.attrs['href']).status_code == 200
    assert client.get(key).json['payload']['title'] == ['Retained Coordinator Draft']
