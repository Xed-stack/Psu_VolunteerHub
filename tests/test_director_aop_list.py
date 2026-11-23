"""Director list scope, filters and exports preserve existing AOP credit."""
import csv
import io
from datetime import datetime
from types import SimpleNamespace as NS
from urllib.parse import parse_qs, urlsplit

import pytest
from app.models import db
from app.models.annual_plan import AnnualTarget
from app.models.event import Campus, Event
from app.report_demo import seed_aop_commitments
from app.services.aop_presentation import director_list
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html
from tests.test_aop_commitments import values


@pytest.fixture
def listed(client, actors):
    sign_in(client, actors, 'director')
    events = [Event(title=f'Synthetic AOP {index}', description='Synthetic', campus_id=1,
        date=datetime(2025,6,1), end_date=datetime(2025,6,2), lifecycle_status='approved') for index in range(13)]
    db.session.add_all(events); db.session.flush()
    seed_aop_commitments(2025, Campus.query.all(), events)
    first = AnnualTarget.query.filter_by(workflow_kind='director_goal').one()
    first.indicator.name = 'Coastal <Outreach>'
    for index in range(11):
        payload = dict(values(), year=2025, title=f'Learning {index}', description='Literacy extension',
                       target_value='2', start_date='2025-01-01', end_date='2025-12-31', action='publish')
        assert client.post('/annual-goals/proposals/new', data=payload).status_code == 302
    db.session.commit()


def test_summary_is_full_scope_and_remaining_is_per_goal(client, app, actors, listed):
    response, data = screen(client, app, '/annual-goals?year=2025')
    assert response.status_code == 200
    assert data['summary']['target'] == 32 and data['summary']['completed'] == 13
    assert data['summary']['remaining'] == 22
    assert data['row_count'] == 12 and len(data['cards']) == 10 and data['pages'] == 2
    _, narrowed = screen(client, app, '/annual-goals?year=2025&q=Coastal')
    assert narrowed['summary'] == data['summary'] and narrowed['row_count'] == 1
    assert narrowed['cards'][0]['rate'] == 130
    assert 'Coastal &lt;Outreach&gt;' in response.text
    page = parse_html(response.text)
    next_link = next(a for a in page.all('a') if a.text == 'Next')
    assert parse_qs(urlsplit(next_link.attrs['href']).query)['year'] == ['2025']


@pytest.mark.parametrize('status,count',[('above',1),('not_started',11),('met',0),('in_progress',0)])
def test_search_and_status_filter_before_pagination(client, app, actors, listed, status, count):
    _, data = screen(client, app, '/annual-goals?year=2025&progress_status='+status)
    assert data['row_count'] == count
    response = client.get('/annual-goals?year=2025&q=NoMatch')
    assert 'No goals match these table filters' in response.text and 'Clear Table Filters' in response.text
    assert client.get('/annual-goals?progress_status=invented').status_code == 400


def test_selected_campus_keeps_director_baseline_and_filtered_exports(client, app, actors, listed):
    _, data = screen(client, app, '/annual-goals?year=2025&campus=2&q=Coastal')
    card = data['cards'][0]
    assert card['result']['target'] == 10 and card['result']['completed'] == 0
    export = client.get('/annual-goals?year=2025&campus=2&q=Coastal&export=csv')
    rows = list(csv.reader(io.StringIO(export.text)))
    assert export.status_code == 200 and len(rows) == 3
    assert rows[2][3] == 'Coastal <Outreach>' and rows[2][6:8] == ['0','10']
    all_rows = list(csv.reader(io.StringIO(client.get('/annual-goals?year=2025&export=csv').text)))
    assert len(all_rows) == 14
    pdf = client.get('/annual-goals?year=2025&q=Coastal&export=pdf')
    assert pdf.status_code == 200 and pdf.data.startswith(b'%PDF')


def test_coordinator_and_legacy_links_keep_existing_behavior(client, actors, listed):
    assert client.get('/annual-goals?year=2025&status=met').status_code == 302
    sign_in(client, actors)
    response = client.get('/annual-goals?year=2025&campus=2')
    assert response.status_code == 200
    assert 'Submit Commitment' in response.text or 'Revise Commitment' in response.text
    assert 'aop-director-summary' not in response.text


def test_progress_statuses_use_counts_and_remaining_cannot_cancel_other_goals():
    from datetime import date
    goals = [NS(id=i,target_value=2,start_date=date(2025,1,1),end_date=date(2025,12,31)) for i in range(4)]
    events = [NS(id=i,campus_id=1,date=datetime(2025,6,1),end_date=datetime(2025,6,2),lifecycle_status='approved') for i in range(3)]
    children = [NS(director_target_id=i,campus_id=1,target_value=8,campus=NS(name='Campus'),
                   activity_mappings=[NS(event_id=e.id,event=e) for e in events[:count]]) for i,count in enumerate((0,1,2,3))]
    cards, totals, _ = director_list(goals,children)
    assert [card['status'] for card in cards] == ['not_started','in_progress','met','above']
    assert totals['remaining'] == 3 and totals['target'] == 8
