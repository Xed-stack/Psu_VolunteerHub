"""Coordinator Needs Attention desktop queue mirrors the Director composition."""
from datetime import timedelta

from app.models import db
from app.models.event import Event, ExternalParticipant, Registration
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_finding_reviews import review_case, active, post
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html


def findings(count=6):
    now = local_now()
    for index in range(count):
        event = Event(title=f'Coordinator finding {index}', description='Synthetic',
                      date=now - timedelta(days=2, minutes=index), end_date=now - timedelta(days=1),
                      campus_id=1, lifecycle_status='approved')
        participant = ExternalParticipant(id_number=f'coord-desktop-{index}', name='Test participant')
        db.session.add_all([event, participant])
        db.session.flush()
        db.session.add(Registration(event_id=event.id, external_participant_id=participant.id, status='confirmed'))
    db.session.commit()


def desktop(page):
    return page.one('div', **{'class': 'needs-desktop'})


def test_coordinator_generated_queue_matches_director_composition(client, app, actors):
    findings()
    sign_in(client, actors)
    response, data = screen(client, app, '/workspace/follow-up?period=all')
    page = parse_html(response.text)
    surface = desktop(page)
    assert page.one('div', **{'class': 'needs-original'})
    assert surface.one('nav', **{'aria-label': 'Coordinator Finding Views'})
    assert surface.one('nav', **{'aria-label': 'Review Categories'})
    assert surface.one('aside', **{'class': 'needs-policy'}).text.startswith('Campus evidence.')
    assert 'Campus Coordinator' in surface.text
    assert len(surface.one('ul', **{'class': 'needs-queue'}).all('li')) == 5
    assert len(data['items']) == 5 and data['total'] >= 6
    assert sum(data['category_counts'].values()) == data['total']
    assert not surface.all('select', **{'id': 'needs-sort'})
    assert 'Export CSV' not in surface.text and 'Remind Coordinator' not in surface.text
    for row in surface.one('ul', **{'class': 'needs-queue'}).all('li'):
        status = [text for text in row.all('p') if 'needs-status' in text.attrs.get('class', '')]
        assert len(status) == 1 and status[0].text in ('Current', 'Past', 'Annual Plan')
        assert row.one('details') and row.one('a', **{'class': 'btn btn--primary'}).text
    assert not page.one('div', **{'class': 'needs-original'}).all('a', **{'href': '#past-findings'})
    assert 'Annual Plans' in page.one('div', **{'class': 'needs-original'}).text


def test_coordinator_category_links_keep_scope_and_counts(client, app, actors):
    findings()
    sign_in(client, actors)
    _, all_data = screen(client, app, '/workspace/follow-up?period=all')
    _, scoped = screen(client, app, '/workspace/follow-up?period=all&review_group=attendance')
    assert scoped['category_counts'] == all_data['category_counts']
    assert all_data['total'] >= 6 and scoped['total'] < all_data['total']
    response, _ = screen(client, app, '/workspace/follow-up?period=all&review_group=attendance')
    page = parse_html(response.text)
    chips = desktop(page).one('nav', **{'aria-label': 'Review Categories'}).all('a')
    assert any('aria-current' in chip.attrs for chip in chips)
    assert '?period=all&review_group=attendance' in chips[1].attrs['href'].replace('&amp;', '&')
    assert client.get('/workspace/follow-up?period=all&review_group=invalid').status_code == 400


def test_coordinator_reviewed_queue_uses_five_rows_and_read_only_actions(client, app, actors, review_case):
    app.config['FINDING_REVIEWS_ENABLED'] = True
    findings(5)
    cases = active(client, app)
    for item in cases:
        assert post(client, item).status_code == 302
    expected = len(cases)
    sign_in(client, actors)
    response, data = screen(client, app, '/workspace/follow-up?period=all&review_tab=reviewed')
    surface = desktop(parse_html(response.text))
    assert data['page_size'] == 5 and data['total'] == expected
    assert data['pages'] == max(1, (expected + 4) // 5)
    assert data['tab_counts']['reviewed'] == expected and sum(data['category_counts'].values()) == expected
    _, generated = screen(client, app, '/workspace/follow-up?period=all')
    assert generated['reviewed_count'] == expected
    assert len(surface.one('ul', **{'class': 'needs-queue'}).all('li')) == 5
    assert 'Export CSV' not in surface.text and 'Remind Coordinator' not in surface.text
    actions = surface.all('a', **{'class': 'btn btn--primary'})
    assert len(actions) == 5 and all(action.text == 'View Assessment' for action in actions)
    assert any(current.text.startswith('Reviewed Recommendations')
               for current in surface.all('a', **{'aria-current': 'page'}))


def test_director_queue_composition_is_unchanged(client, app, review_case):
    response, data = screen(client, app, '/workspace/follow-up?period=all')
    surface = desktop(parse_html(response.text))
    assert surface.one('nav', **{'aria-label': 'Director Review Views'})
    assert surface.one('form', **{'class': 'needs-sort'})
    assert 'Export CSV' in surface.text and data['page_size'] == 5
