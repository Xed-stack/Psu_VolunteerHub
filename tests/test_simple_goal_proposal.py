from app.models import db
from app.models.annual_plan import AnnualGoalProposal
from tests.test_app import app, client, _create_user
from tests.test_annual_goals import _login_as, definition
from tests.html_helpers import parse_html, form_with_control


def test_director_form_uses_dated_aop_goal_fields(app, client):
    director = _create_user(app, role='director', campus_id=1)
    _login_as(client, director)
    page = parse_html(client.get('/annual-goals/proposals/new').get_data(as_text=True))
    form = form_with_control(page,'target_value')
    fields = {element.attrs['name'] for tag in ('input','select','textarea')
              for element in form.all(tag) if element.attrs.get('type') != 'hidden' and element.attrs.get('name')}
    assert fields == {'year','title','description','target_value','start_date','end_date'}
    assert 'ASP' not in page.text and not form.all('select')


def test_existing_proposal_payload_and_history_survive_blocked_edit(app, client):
    coordinator = _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, coordinator)
    original = definition()
    history = [dict(action='submitted',payload=original)]
    proposal = AnnualGoalProposal(campus_id=1,proposed_by_id=coordinator,payload=original,history=history)
    db.session.add(proposal);db.session.commit()
    assert client.post(f'/annual-goals/proposals/{proposal.id}/edit',data=dict(original,target_value='8')).status_code == 409
    db.session.refresh(proposal)
    assert proposal.payload == original and proposal.history == history
