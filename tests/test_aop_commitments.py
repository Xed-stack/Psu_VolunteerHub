from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import re

import pytest
from sqlalchemy import text

from app.models import db
from app.models.annual_plan import AnnualTarget, AnnualGoalProposal, AnnualActivityMapping
from app.models.event import Event
from app.models.notification import Notification
from app.services import aop_goals as aop
from app.annual_goals import summary
from app.aop_migration import migrate_aop
from tests.test_app import app, client, _create_user
from tests.test_annual_goals import _login_as


def values(**changes):
    return dict(year=2026, title='Community Learning', description='Campus outreach activities',
                target_value='10', start_date='2026-06-01', end_date='2026-08-31', **changes)


def hidden(response, name):
    return re.search(r'name="' + name + r'" value="([^"]*)"', response.get_data(as_text=True)).group(1)


def publish(client, **changes):
    payload = dict(values(), **changes)
    response = client.post('/annual-goals/proposals/new', data=dict(payload, action='publish'))
    assert response.status_code == 302
    return AnnualTarget.query.filter_by(workflow_kind='director_goal').one()


def submit(client, goal, count, action='submit'):
    path = f'/annual-goals/targets/{goal.id}/commitment'
    form = client.get(path)
    return client.post(path, data=dict(target_value=count, action=action, note='Campus commitment',
                                      version=hidden(form, 'version'), goal_version=hidden(form, 'goal_version')))


@pytest.mark.parametrize('changes', [dict(start_date=''), dict(end_date=''),
    dict(start_date='2026-09-01'), dict(end_date='2027-01-01'), dict(target_value='0'),
    dict(target_value='1.5'), dict(target_value='1e2'), dict(target_value='-1')])
def test_definition_rejects_invalid_dates_and_counts(changes):
    with pytest.raises(ValueError):
        aop.definition(dict(values(), **changes))


def test_entire_period_boundaries_and_exact_completion():
    goal = SimpleNamespace(start_date=date(2026, 6, 1), end_date=date(2026, 8, 31))
    event = SimpleNamespace(date=datetime(2026, 6, 1), end_date=datetime(2026, 8, 31, 23, 59, 59), lifecycle_status='approved')
    assert aop.activity_state(event, goal, event.end_date-timedelta(microseconds=1)) == 'Not Yet Completed'
    assert aop.activity_state(event, goal, event.end_date) == 'Completed'
    event.end_date = datetime(2026, 9, 1)
    assert aop.activity_state(event, goal) == 'Outside Goal Period'
    event.end_date = datetime(2026, 6, 2)
    event.date = datetime(2026, 5, 31, 23, 59)
    assert aop.activity_state(event, goal) == 'Outside Goal Period'
    event.date = datetime(2026, 5, 31, 16, tzinfo=timezone.utc)
    assert aop.activity_state(event, goal, datetime(2026, 9, 1)) == 'Completed'
    event.lifecycle_status = 'cancelled'
    assert aop.activity_state(event, goal) == 'Activity Not Approved'
    event.end_date = None
    assert aop.activity_state(event, goal) == 'Schedule Incomplete'
    assert aop.definition(dict(values(), start_date='2026-08-31', end_date='2026-08-31'))


def test_immediate_commitments_exceed_target_and_no_attendance_gate(app, client):
    director = _create_user(app, email='director-aop@test.com', role='director', campus_id=1)
    c1 = _create_user(app, email='campus1-aop@test.com', role='coordinator', campus_id=1)
    c2 = _create_user(app, email='campus2-aop@test.com', role='coordinator', campus_id=2)
    _login_as(client, director)
    goal = publish(client)
    assert Notification.query.filter_by(notification_type='aop_goal').count() == 2
    _login_as(client, c1)
    assert submit(client, goal, '7').status_code == 302
    _login_as(client, c2)
    assert submit(client, goal, '6').status_code == 302
    assert summary(2026)['rows'][0]['actual'] == 0
    children = aop.commitments([goal.id])
    assert sum(int(child.target_value) for child in children) == 13
    for child in children:
        for index in range(6):
            event = Event(title=f'Completed {child.campus_id}-{index}', description='Synthetic', campus_id=child.campus_id,
                          date=datetime(2026, 7, 1, 8), end_date=datetime(2026, 7, 1, 9), lifecycle_status='approved', slots=10)
            db.session.add(event)
            db.session.flush()
            db.session.add(AnnualActivityMapping(target_id=child.id, event_id=event.id))
    db.session.commit()
    result = aop.progress(goal, aop.commitments([goal.id]))
    assert (result['completed'], result['remaining'], result['exceeded']) == (12, 0, 2)
    assert summary(2026)['rows'][0]['actual'] == 12
    assert summary(2026, 1)['rows'][0]['actual'] == 6
    assert goal.target_value == 10
    _login_as(client, director)
    assert client.get(f'/annual-goals/targets/{goal.id}').status_code == 200
    assert client.get('/annual-goals?year=2026&export=csv').status_code == 200
    assert client.get('/annual-goals?year=2026&export=pdf').status_code == 200
    assert Notification.query.filter_by(user_id=director, notification_type='aop_goal').count() == 2
    assert 'AOP Commitment Updated' in client.get('/notifications').get_data(as_text=True)


def test_drafts_revisions_and_stale_commitments(app, client):
    director = _create_user(app, email='director-draft@test.com', role='director', campus_id=1)
    coordinator = _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, director)
    goal = publish(client)
    _login_as(client, coordinator)
    assert submit(client, goal, '7', 'save').status_code == 302
    assert aop.commitments([goal.id]) == []
    assert submit(client, goal, '7').status_code == 302
    assert submit(client, goal, '15', 'save').status_code == 302
    child = AnnualTarget.query.filter_by(director_target_id=goal.id).one()
    assert child.target_value == 7
    path = f'/annual-goals/targets/{goal.id}/commitment'
    stale = client.get(path)
    assert submit(client, goal, '15').status_code == 302
    assert child.target_value == 15
    assert client.post(path, data=dict(action='submit', target_value='2', version=hidden(stale, 'version'),
                                      goal_version=hidden(stale, 'goal_version'))).status_code == 400
    assert child.target_value == 15
    assert AnnualTarget.query.filter_by(director_target_id=goal.id).count() == 1
    proposal = AnnualGoalProposal.query.filter_by(campus_id=1).one()
    assert [entry['payload']['target_value'] for entry in proposal.history if entry['action'] == 'commitment_submitted'] == [7, 15]
    assert client.post(f'/annual-goals/proposals/{proposal.id}', data=dict(action='approve')).status_code == 409


def test_link_ownership_and_out_of_period_activity(app, client):
    director = _create_user(app, email='director-link@test.com', role='director', campus_id=1)
    c1 = _create_user(app, role='coordinator', campus_id=1)
    c2 = _create_user(app, email='other-link@test.com', role='coordinator', campus_id=2)
    _login_as(client, director)
    goal = publish(client)
    _login_as(client, c1)
    submit(client, goal, '2')
    for campus, start in [(1, 7), (1, 5), (2, 7)]:
        db.session.add(Event(title=f'Activity {campus}-{start}', description='Synthetic', campus_id=campus,
            date=datetime(2026, start, 1), end_date=datetime(2026, start, 2), lifecycle_status='approved', slots=10))
    db.session.commit()
    events = Event.query.filter(Event.title.like('Activity %')).all()
    path = f'/annual-goals/targets/{goal.id}/link-activities'
    for event in events:
        form = client.get(path)
        response = client.post(path, data=dict(event_id=str(event.id), version=hidden(form, 'version'),
                                              goal_version=hidden(form, 'goal_version')))
        assert response.status_code == (302 if event.campus_id == 1 and event.date.month == 7 else 400)
    child = AnnualTarget.query.filter_by(director_target_id=goal.id).one()
    _login_as(client, c2)
    assert client.get(f'/annual-goals/targets/{child.id}').status_code == 403
    assert client.get(path).status_code == 404


def test_period_revision_requires_review_and_retains_links(app, client):
    director = _create_user(app, email='director-period@test.com', role='director', campus_id=1)
    c1 = _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, director)
    goal = publish(client)
    _login_as(client, c1)
    submit(client, goal, '1')
    child = AnnualTarget.query.filter_by(director_target_id=goal.id).one()
    event = Event(title='July Activity', description='Synthetic', campus_id=1, slots=10, lifecycle_status='approved',
                  date=datetime(2026, 7, 1), end_date=datetime(2026, 7, 2))
    db.session.add(event)
    db.session.flush()
    db.session.add(AnnualActivityMapping(target_id=child.id, event_id=event.id))
    db.session.commit()
    _login_as(client, director)
    path = f'/annual-goals/proposals/new?target_id={goal.id}'
    form = client.get(path)
    data = dict(values(), start_date='2026-08-01', action='publish', version=hidden(form, 'version'),
                target_version=hidden(form, 'target_version'))
    preview = client.post(path, data=data)
    assert preview.status_code == 200
    assert goal.start_date == date(2026, 6, 1)
    assert '1 before' in preview.get_data(as_text=True)
    data.update(impact_token=hidden(preview, 'impact_token'), confirm_period='yes')
    assert client.post(path, data=data).status_code == 302
    assert goal.start_date == date(2026, 8, 1)
    assert AnnualActivityMapping.query.count() == 1
    assert summary(2026)['rows'][0]['actual'] == 0


def test_notification_failure_rolls_back_publication(app, client, monkeypatch):
    director = _create_user(app, role='director', campus_id=1)
    _login_as(client, director)
    def fail(*args, **kwargs):
        from sqlalchemy.exc import SQLAlchemyError
        raise SQLAlchemyError('Synthetic notification failure')
    monkeypatch.setattr(aop, 'notifications', fail)
    response=client.post('/annual-goals/proposals/new', data=dict(values(), action='publish'))
    assert response.status_code==503 and b'No changes were saved' in response.data
    assert AnnualTarget.query.count() == 0


def test_asp_archive_dry_run_and_rerun(app):
    with db.engine.begin() as connection:
        connection.execute(text("INSERT INTO annual_plans (id,source_key,year,plan_type,title,status,source_document,imported_at) VALUES (99,'old-asp',2026,'ASP','Archived','approved','Original','2026-01-01')"))
        connection.execute(text("INSERT INTO annual_indicators (id,source_key,plan_id,code,program,name,unit,responsible_office,evidence_basis) VALUES (99,'old-asp',99,'OLD','Original','Archived','activities','PSU','activities')"))
        connection.execute(text("INSERT INTO annual_targets (id,source_key,indicator_id,target_value,comparison_rule,is_active) VALUES (99,'old-asp',99,10,'gte',1)"))
    dry = migrate_aop(db.engine, ':memory:')
    assert dry['archive']['annual_plans'] == 1
    with db.engine.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM annual_plans')).scalar() == 1
    migrate_aop(db.engine, ':memory:', dry_run=False)
    with db.engine.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM annual_plans')).scalar() == 0
        assert connection.execute(text('SELECT COUNT(*) FROM retired_annual_archive')).scalar() == 3
    assert migrate_aop(db.engine, ':memory:', dry_run=False)['archive']['annual_plans'] == 0


def test_asp_requests_retired_and_legacy_writes_blocked(app, client):
    director = _create_user(app, role='director', campus_id=1)
    _login_as(client, director)
    assert client.get('/annual-goals?plan=ASP').status_code == 410
    assert client.post('/annual-goals/targets/99/evidence', data={}).status_code == 409


def test_unpublished_drafts_remain_private_and_gets_do_not_write(app, client):
    from tests.test_system_performance import query_count
    director = _create_user(app, email='private-director@test.com', role='director', campus_id=1)
    coordinator = _create_user(app, role='coordinator', campus_id=1)
    _login_as(client, director)
    goal = publish(client)
    path = f'/annual-goals/proposals/new?target_id={goal.id}'
    form = client.get(path)
    assert client.post(path, data=dict(values(), description='Unpublished Director Explanation', action='save',
        version=hidden(form,'version'), target_version=hidden(form,'target_version'))).status_code == 302
    _login_as(client, coordinator)
    assert 'Unpublished Director Explanation' not in client.get(f'/annual-goals/targets/{goal.id}').get_data(as_text=True)
    path = f'/annual-goals/targets/{goal.id}/commitment'
    form = client.get(path)
    client.post(path, data=dict(target_value='8',note='Private Campus Explanation',action='save',
        version=hidden(form,'version'),goal_version=hidden(form,'goal_version')))
    _login_as(client,director)
    with query_count(app) as statements:
        response = client.get(f'/annual-goals/targets/{goal.id}')
    assert 'Private Campus Explanation' not in response.get_data(as_text=True)
    assert not any(statement.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for statement in statements)


def test_archive_conflict_rolls_back_without_removing_events(app):
    from app.aop_migration import archive
    archive.create(db.engine)
    event_count = Event.query.count()
    with db.engine.begin() as connection:
        connection.execute(text("INSERT INTO annual_plans (id,source_key,year,plan_type,title,status,source_document,imported_at) VALUES (99,'old-asp',2026,'ASP','Original','approved','Original','2026-01-01')"))
        connection.execute(archive.insert().values(source_table='annual_plans',source_id=99,payload='conflicting archive'))
    with pytest.raises(ValueError,match='Archive identity conflict'):
        migrate_aop(db.engine,':memory:',dry_run=False)
    with db.engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM annual_plans WHERE id=99")).scalar() == 'Original'
    assert Event.query.count() == event_count


def test_upgrade_adds_workflow_columns_to_old_schema():
    from sqlalchemy import create_engine, inspect
    engine = create_engine('sqlite:///:memory:')
    statements = [
        'CREATE TABLE annual_plans (id INTEGER PRIMARY KEY, plan_type TEXT)',
        'CREATE TABLE annual_indicators (id INTEGER PRIMARY KEY, plan_id INTEGER)',
        'CREATE TABLE annual_targets (id INTEGER PRIMARY KEY, indicator_id INTEGER, campus_id INTEGER)',
        'CREATE TABLE annual_results (id INTEGER PRIMARY KEY, target_id INTEGER)',
        'CREATE TABLE annual_activity_mappings (id INTEGER PRIMARY KEY, target_id INTEGER, event_id INTEGER)',
        'CREATE TABLE annual_goal_proposals (id INTEGER PRIMARY KEY, campus_id INTEGER, payload TEXT, published_target_id INTEGER, replaces_target_id INTEGER)']
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    dry = migrate_aop(engine,':memory:')
    assert len(dry['schema']) == 10
    assert 'version' not in {column['name'] for column in inspect(engine).get_columns('annual_targets')}
    migrate_aop(engine,':memory:',dry_run=False)
    assert {'version','workflow_kind','start_date','end_date','director_target_id'} <= {
        column['name'] for column in inspect(engine).get_columns('annual_targets')}
    assert migrate_aop(engine,':memory:')['schema'] == []
    engine.dispose()


def test_older_filters_open_history_without_silently_broadening_scope(app, client):
    director = _create_user(app, role='director', campus_id=1)
    _login_as(client,director)
    response = client.get('/annual-goals?year=2026&office=Original+Office&status=met')
    assert response.status_code==302
    from urllib.parse import parse_qs, urlsplit
    query=parse_qs(urlsplit(response.location).query)
    assert query['history']==['1'] and query['office']==['Original Office'] and query['status']==['met']
    assert client.get('/annual-goals?plan=invalid').status_code==400


@pytest.mark.parametrize('basis', ['approved_aggregate','unique_attendees'])
def test_retired_shared_evidence_preserves_aop_history_without_conversion(app, client, basis):
    from tests.test_annual_goals import target
    from app.models.event import Registration, Attendance
    original=target(campus=1,shared='retained-shared',basis=basis,value=1)
    year=original.indicator.plan.year
    event=Event(title='Retained Shared Activity',description='Synthetic',campus_id=1,slots=10,
        date=datetime(year,7,1,8),end_date=datetime(year,7,1,9),lifecycle_status='approved')
    user_id=_create_user(app,role='volunteer',campus_id=1)
    db.session.add(event);db.session.flush()
    registration=Registration(event_id=event.id,user_id=user_id,status='confirmed')
    db.session.add(registration);db.session.flush()
    db.session.add(Attendance(event_id=event.id,user_id=user_id,registration_id=registration.id,status='present'))
    db.session.commit()
    with db.engine.begin() as connection:
        connection.execute(text("INSERT INTO annual_plans (id,source_key,year,plan_type,title,status,source_document,imported_at) VALUES (99,'shared-asp',:year,'ASP','Retired source','approved','Original shared source',:at)"),dict(year=year,at=f'{year}-01-01'))
        connection.execute(text("INSERT INTO annual_indicators (id,source_key,plan_id,code,program,name,unit,responsible_office,evidence_basis,shared_key) VALUES (99,'shared-asp',99,'SHARED','Community learning','Delivered programs','programs','Extension Office',:basis,'retained-shared')"),dict(basis=basis))
        connection.execute(text("INSERT INTO annual_targets (id,source_key,indicator_id,campus_id,target_value,comparison_rule,is_active) VALUES (99,'shared-asp',99,1,1,'gte',1)"))
        if basis=='approved_aggregate':
            connection.execute(text("INSERT INTO annual_results (id,source_key,target_id,actual_value,evidence_status,result_type,source_document,coverage_note,coverage_start,coverage_end,imported_at) VALUES (99,'shared-asp',99,1,'verified','approved_aggregate','Original shared report','Original coverage',:start,:end,:end)"),dict(start=f'{year}-01-01',end=f'{year}-07-01'))
        else:
            connection.execute(text('INSERT INTO annual_activity_mappings (id,target_id,event_id) VALUES (99,99,:event)'),dict(event=event.id))
    migrate_aop(db.engine,':memory:',dry_run=False)
    result=summary(year,1,historical=True)
    assert result['total']==result['met']==1 and result['rows'][0]['actual']==1
    assert result['rows'][0]['target_id']==original.id and result['rows'][0]['plan_types']==['AOP']
    assert summary(year,1)['total']==0
    assert AnnualTarget.query.count()==1
    if basis=='approved_aggregate':
        from app.models.annual_plan import AnnualResult
        assert AnnualResult.query.count()==0
    director=_create_user(app,email='history-director@test.com',role='director',campus_id=1)
    _login_as(client,director)
    response=client.get(f'/annual-goals/targets/{original.id}')
    assert response.status_code==200 and b'Retained Shared Evidence' in response.data
