"""Dated AOP goals and immediate campus commitments; no attendance gate."""
import json
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

from flask_login import current_user
from sqlalchemy import update
from sqlalchemy.orm import joinedload, selectinload

from app.models import db
from app.models.annual_plan import (AnnualPlan, AnnualIndicator, AnnualTarget,
                                   AnnualGoalProposal, AnnualActivityMapping)
from app.models.event import Event
from app.models.user import User
from app.models.notification import notify
from app.reports import ReportError
from app.performance import request_value
from app.services.activity_workflow import local_now


def activity_count(value):
    text = str(value or '')
    if not text.isascii() or not text.isdigit() or not 1 <= int(text) <= 10**12:
        raise ReportError('Enter a whole number from 1 to 1 trillion.')
    return int(text)


def definition(data):
    from app.annual_goals import selected_year
    year = selected_year(data.get('year'))
    title = str(data.get('title', '')).strip()
    description = str(data.get('description', '')).strip()
    if not title or len(title) > 255 or len(description) > 4000:
        raise ReportError('Enter a goal title within 255 characters and a description within 4,000 characters.')
    try:
        start = date.fromisoformat(data.get('start_date', ''))
        end = date.fromisoformat(data.get('end_date', ''))
        if start > end or start.year != year or end.year != year:
            raise ValueError()
    except (ValueError, TypeError):
        raise ReportError('Choose ordered Start Date and End Date values within the AOP year.') from None
    return dict(year=year, title=title, description=description,
                target_value=activity_count(data.get('target_value')),
                start_date=start.isoformat(), end_date=end.isoformat())


def pht(value):
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
    return value


def activity_state(event, goal, now=None):
    """Use a half-open date period so the entire last Philippine day is included."""
    start, end = pht(event.date), pht(event.end_date)
    if not start or not end or end <= start:
        return 'Schedule Incomplete'
    if not goal.start_date or not goal.end_date:
        return 'Goal Period Missing'
    if start < datetime.combine(goal.start_date, time.min) or end >= datetime.combine(goal.end_date + timedelta(days=1), time.min):
        return 'Outside Goal Period'
    if event.lifecycle_status != 'approved':
        return 'Activity Not Approved'
    return 'Completed' if end <= pht(now or local_now()) else 'Not Yet Completed'


def audit(proposal, action, payload=None):
    proposal.history = [*(proposal.history or []), dict(
        action=action, actor=current_user.id, at=datetime.utcnow().isoformat(),
        payload=dict(payload if payload is not None else proposal.payload))]


def claim(record, version):
    """Compare-and-swap also protects databases where FOR UPDATE is unavailable."""
    try:
        expected = int(version)
    except (TypeError, ValueError):
        raise ReportError('Reload this page before saving; its version is missing.') from None
    result = db.session.execute(update(type(record)).where(
        type(record).id == record.id, type(record).version == expected
    ).values(version=expected + 1))
    if result.rowcount != 1:
        raise ReportError('This record changed. Reload it before saving your changes.')


def lock_goal(goal, version):
    result = db.session.execute(update(AnnualTarget).where(
        AnnualTarget.id == goal.id, AnnualTarget.version == version
    ).values(version=version))
    if result.rowcount != 1:
        raise ReportError('The Director goal changed. Reload its target and dates before saving.')


def notifications(goal, text, *, directors=False):
    recipients = User.query.filter(User._is_active.is_(True),
        User.role == ('director' if directors else 'coordinator'))
    if not directors:
        recipients = recipients.filter(User.campus_id.isnot(None))
    for user in recipients.all():
        notify(user.id, 'AOP Commitment Updated' if directors else 'AOP Goal Published or Updated',
               json.dumps(dict(goal_id=goal.id, text=text)), notification_type='aop_goal', commit=False)


def goals(year):
    return AnnualTarget.query.join(AnnualIndicator).join(AnnualPlan).filter(
        AnnualTarget.workflow_kind == 'director_goal', AnnualTarget.is_active.is_(True),
        AnnualPlan.plan_type == 'AOP', AnnualPlan.year == year
    ).options(joinedload(AnnualTarget.indicator).joinedload(AnnualIndicator.plan)).order_by(
        AnnualTarget.start_date, AnnualTarget.id).all()


def commitments(goal_ids):
    return AnnualTarget.query.filter(AnnualTarget.workflow_kind == 'campus_commitment',
        AnnualTarget.director_target_id.in_(goal_ids), AnnualTarget.is_active.is_(True)
    ).options(joinedload(AnnualTarget.campus), selectinload(AnnualTarget.activity_mappings).joinedload(
        AnnualActivityMapping.event).joinedload(Event.campus)).order_by(AnnualTarget.campus_id).all()


def dataset(year):
    def load():
        parents = goals(year)
        return parents, commitments([goal.id for goal in parents])
    return request_value(('dated-aop-data', year), load)


def progress(goal, children, campus_id=None):
    selected = [child for child in children if child.director_target_id == goal.id
                and (campus_id is None or child.campus_id == campus_id)]
    records = {mapping.event_id: mapping.event for child in selected
               for mapping in child.activity_mappings if mapping.event.campus_id == child.campus_id}
    states = [dict(event=event, state=activity_state(event, goal)) for event in records.values()]
    actual = sum(item['state'] == 'Completed' for item in states)
    target = int(goal.target_value) if campus_id is None else sum(int(child.target_value) for child in selected)
    return dict(target=target, completed=actual, remaining=max(target-actual, 0),
                exceeded=max(actual-target, 0), activities=states, commitments=selected)


def rows(year, campus_id=None, data=None):
    """Supply the existing annual reporting interface using only the new workflow."""
    parents, children = data if data is not None else dataset(year)
    result = []
    for goal in parents:
        scope = progress(goal, children, campus_id)
        if campus_id is not None and not scope['commitments']:
            continue
        target = goal if campus_id is None else scope['commitments'][0]
        result.append(dict(target_id=target.id, code=goal.indicator.code, name=goal.indicator.name,
            program=goal.indicator.program, definition=goal.indicator.definition, unit='activities',
            responsible_office=goal.indicator.responsible_office, target=scope['target'], actual=scope['completed'],
            met=scope['completed'] >= scope['target'], pending=False, verified=True,
            deadline=goal.end_date, overdue=goal.end_date < local_now().date() and bool(scope['remaining']),
            comparison_rule='gte', rule_label='At Least', plan_types=['AOP'], plan_type='AOP', shared_key=None,
            basis='Linked approved ended activities', source_document='Director-published AOP goal',
            coverage_note=f'{goal.start_date} through {goal.end_date}, inclusive, Philippine time; entire activity schedule required.',
            start_date=goal.start_date, end_date=goal.end_date,
            events=[dict(id=item['event'].id, title=item['event'].title) for item in scope['activities']],
            aggregate_sex=None, status='Target Met' if not scope['remaining'] else 'Activities Remaining'))
    return result


def publish(proposal, payload, target=None):
    if target and target.indicator.plan.year != payload['year']:
        raise ReportError('A published goal’s AOP year cannot change.')
    if target is None:
        key = f'aop:{uuid4().hex}'
        plan = AnnualPlan(source_key=key, year=payload['year'], plan_type='AOP',
            title=payload['title'], source_document='Director-published AOP goal',
            approval_reference=f'Director {current_user.id}', approval_date=local_now().date())
        indicator = AnnualIndicator(source_key=key, plan=plan, code=key, program='Annual Operational Plan',
            name=payload['title'], unit='activities', responsible_office='PSU', evidence_basis='activities')
        target = AnnualTarget(source_key=key, indicator=indicator, workflow_kind='director_goal',
                              target_value=payload['target_value'])
        db.session.add(target)
        db.session.flush()
    target.indicator.name = payload['title']
    target.indicator.definition = payload['description']
    target.indicator.plan.title = payload['title']
    target.target_value = payload['target_value']
    target.start_date = date.fromisoformat(payload['start_date'])
    target.end_date = date.fromisoformat(payload['end_date'])
    target.deadline = target.end_date
    proposal.published_target_id = target.id
    proposal.status = 'published'
    audit(proposal, 'published')
    notifications(target, f"{payload['title']}: {payload['target_value']} activities, {target.start_date} through {target.end_date} (PHT).")
    return target


def submit_commitment(proposal, goal, count):
    target = db.session.get(AnnualTarget, proposal.published_target_id) if proposal.published_target_id else None
    if target is None:
        target = AnnualTarget(source_key=f'commitment:{uuid4().hex}', indicator_id=goal.indicator_id,
            campus_id=proposal.campus_id, director_target_id=goal.id,
            workflow_kind='campus_commitment', target_value=count)
        db.session.add(target)
        db.session.flush()
    else:
        target.target_value = count
        target.version += 1
    proposal.published_target_id = target.id
    proposal.status = 'submitted'
    audit(proposal, 'commitment_submitted')
    notifications(goal, f"{target.campus.name} committed to {count} activities for {goal.indicator.name}.", directors=True)
    return target


def available_goals(campus_id):
    children = AnnualTarget.query.filter_by(workflow_kind='campus_commitment', campus_id=campus_id,
                                            is_active=True).all()
    return AnnualTarget.query.filter(AnnualTarget.id.in_([child.director_target_id for child in children]),
        AnnualTarget.workflow_kind == 'director_goal', AnnualTarget.is_active.is_(True)
    ).options(joinedload(AnnualTarget.indicator)).order_by(AnnualTarget.start_date).all()


def validate_links(goal_ids, campus_id, start, end, existing=()):
    available = {str(goal.id): goal for goal in available_goals(campus_id)}
    for identity in goal_ids:
        goal = available.get(str(identity))
        if goal is None:
            raise ReportError('Choose AOP goals with a submitted commitment for your campus.')
        # Retained links may become ineligible after an audited period or schedule correction.
        if str(identity) in {str(value) for value in existing}:
            continue
        from types import SimpleNamespace
        state = activity_state(SimpleNamespace(date=start, end_date=end, lifecycle_status='approved'), goal)
        if state not in ('Completed', 'Not Yet Completed'):
            raise ReportError(f'{goal.indicator.name}: the entire activity schedule must be within the goal period.')


def sync_links(event, goal_ids):
    children = AnnualTarget.query.filter_by(workflow_kind='campus_commitment', campus_id=event.campus_id,
                                            is_active=True).all()
    for child in children:
        link = AnnualActivityMapping.query.filter_by(target_id=child.id, event_id=event.id).first()
        selected = str(child.director_target_id) in {str(value) for value in goal_ids}
        if selected != bool(link):
            goal = db.session.get(AnnualTarget, child.director_target_id)
            lock_goal(goal, goal.version)
            db.session.refresh(goal)
            if selected:
                validate_links([goal.id], event.campus_id, event.date, event.end_date)
        if selected and not link:
            db.session.add(AnnualActivityMapping(target_id=child.id, event_id=event.id))
        elif link and not selected:
            db.session.delete(link)
        else:
            continue
        proposal = AnnualGoalProposal.query.filter_by(published_target_id=child.id,
                                                      workflow_kind='campus_commitment').one()
        claim(proposal, proposal.version)
        audit(proposal, 'activity_linked' if selected else 'activity_unlinked', dict(event_id=event.id))


def linked_goal_ids(event):
    return [str(row.director_target_id) for row in AnnualTarget.query.join(AnnualActivityMapping).filter(
        AnnualActivityMapping.event_id == event.id, AnnualTarget.workflow_kind == 'campus_commitment')]


def choices(campus_id):
    from types import SimpleNamespace
    return [SimpleNamespace(id=goal.id, name=f'{goal.indicator.name} ({goal.start_date} to {goal.end_date}, PHT)')
            for goal in available_goals(campus_id)]
