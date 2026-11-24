"""AOP publication, immediate campus commitments, and scoped activity linking."""
from types import SimpleNamespace

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import db
from app.models.annual_plan import AnnualTarget, AnnualGoalProposal
from app.models.event import Event, Campus
from app.campuses import campus_query
from app.pagination import paginate
from app.reports import ReportError
from app.services import aop_goals as aop
from app.services.activity_workflow import local_now
from app.utils.decorators import roles_required
from app.routes.goals import goals_bp, campus_scope, reject_sample_write


def goal_record(target_id):
    target = db.get_or_404(AnnualTarget, target_id)
    if target.workflow_kind == 'campus_commitment':
        if current_user.role == 'coordinator' and target.campus_id != current_user.campus_id:
            abort(403)
        target = db.get_or_404(AnnualTarget, target.director_target_id)
    if target.workflow_kind != 'director_goal' or not target.is_active:
        abort(404)
    if current_user.role == 'coordinator' and current_user.campus_id is None:
        abort(403)
    return target


def index():
    from app.annual_goals import selected_year, summarize
    from app.routes.goals import export_rows
    if request.args.get('plan') == 'ASP':
        abort(410, description='ASP has been retired.')
    if request.args.get('plan', '') not in ('', 'AOP'):
        abort(400, description='Choose a valid AOP scope.')
    if any(request.args.get(key) for key in ('program', 'office', 'status', 'basis')):
        return redirect(url_for('goals.details', **dict(request.args.to_dict(flat=False), history=1)))
    if request.args.get('sample') == '1':
        if request.args.get('export'):
            abort(400, description='Sample figures cannot be exported as official results.')
        return redirect(url_for('goals.details', history=1, sample=1, year=request.args.get('year')))
    try:
        year = selected_year(request.args.get('year'))
    except ReportError as exc:
        abort(400, description=str(exc))
    campus_id = campus_scope()
    parents, children = aop.dataset(year)
    presentation = {}
    if current_user.role == 'director':
        from app.services.aop_presentation import director_list, STATUSES
        cards, totals, breakdown = director_list(parents, children, campus_id)
        active_goals = len(cards)
        search = request.args.get('q', '').strip()[:200]
        status = request.args.get('progress_status', '')
        if status not in ('', *STATUSES):
            abort(400, description='Choose a listed progress status.')
        cards = [card for card in cards if
                 (not search or search.casefold() in (card['goal'].indicator.name + ' ' +
                  (card['goal'].indicator.definition or '') + ' ' +
                  ' '.join(child.campus.name for child in card['result']['commitments'])).casefold()) and
                 (not status or card['status'] == status)]
        presentation = dict(summary=totals, breakdown=breakdown, q=search,
                            progress_status=status, statuses=STATUSES, row_count=len(cards), active_goals=active_goals)
    if request.args.get('export'):
        if current_user.role == 'director':
            source = {row['target_id']: row for row in aop.rows(year, data=(parents, children))}
            rows = [dict(source[card['goal'].id], actual=card['result']['completed'],
                         met=card['result']['completed'] >= card['result']['target'],
                         overdue=card['goal'].end_date < local_now().date() and bool(card['result']['remaining']),
                         status=STATUSES[card['status']]) for card in cards]
            return export_rows(rows, summarize(rows, year, campus_id),
                               dict(q=search, progress_status=status, baseline='University Director target'),
                               request.args['export'])
        rows = aop.rows(year, campus_id)
        return export_rows(rows, summarize(rows, year, campus_id), {}, request.args['export'])
    if current_user.role != 'director':
        cards = [dict(goal=goal, university=aop.progress(goal, children),
                  campus=aop.progress(goal, children, campus_id) if campus_id else None)
             for goal in parents]
    drafts = AnnualGoalProposal.query.filter(AnnualGoalProposal.workflow_kind != 'legacy')
    if current_user.role == 'coordinator':
        drafts = drafts.filter_by(campus_id=current_user.campus_id)
    else:
        drafts = drafts.filter_by(campus_id=None)
    drafts = drafts.filter_by(status='draft').order_by(AnnualGoalProposal.created_at.desc()).all()
    if current_user.role == 'admin':
        drafts = []
    page = max(1, request.args.get('page', 1, type=int))
    pages = max(1, (len(cards)+9)//10)
    page = min(page, pages)
    campuses = campus_query().order_by(Campus.name).all()
    if current_user.role == 'director':
        submitted = {row['id']: row for row in breakdown}
        presentation['campus_tiles'] = [dict(id=campus.id, name=campus.name,
            committed=submitted.get(campus.id, {}).get('committed', 0),
            completed=submitted.get(campus.id, {}).get('completed', 0),
            submitted=campus.id in submitted)
            for campus in campuses if campus_id is None or campus.id == campus_id]
    template = ('goals/director_aop_index.html' if current_user.role == 'director'
                else 'goals/coordinator_aop_index.html' if current_user.role == 'coordinator'
                else 'goals/aop_index.html')
    return render_template(template, cards=cards[(page-1)*10:page*10], year=year,
                           page=page, pages=pages, campus_id=campus_id, drafts=drafts, today=local_now().date(),
                           campuses=campuses,
                           campus_name=db.session.get(Campus,campus_id).name if campus_id else None,
                           **presentation)


def edit_goal(proposal_id=None):
    reject_sample_write()
    if proposal_id:
        from app.routes.goals import owned_proposal
        requested = owned_proposal(proposal_id)
        if requested.workflow_kind == 'legacy':
            abort(409, description='Historical AOP records are read-only.')
    if current_user.role != 'director':
        if request.method == 'POST':
            abort(403)
        return redirect(url_for('goals.workspace'))
    if request.args.get('revise'):
        abort(409, description='Historical AOP records are read-only. Post a new dated goal instead.')
    proposal = db.get_or_404(AnnualGoalProposal, proposal_id) if proposal_id else None
    if proposal and (proposal.workflow_kind != 'director_goal' or proposal.campus_id is not None):
        abort(409, description='Historical AOP records are read-only.')
    target_id = proposal.published_target_id if proposal else request.args.get('target_id', type=int)
    target = goal_record(target_id) if target_id else None
    if target and not proposal:
        proposal = AnnualGoalProposal.query.filter_by(published_target_id=target.id,
                                                      workflow_kind='director_goal').one()
    values = dict(proposal.payload) if proposal else dict(year=local_now().year)
    if target and request.method == 'GET' and proposal.status != 'draft':
        values = dict(year=target.indicator.plan.year, title=target.indicator.name,
            description=target.indicator.definition or '', target_value=int(target.target_value),
            start_date=target.start_date.isoformat(), end_date=target.end_date.isoformat())
    error, impact = None, None
    failure_status = 400
    if request.method == 'POST':
        values = request.form.to_dict()
        try:
            payload = aop.definition(request.form)
            action = request.form.get('action')
            if action not in ('save', 'publish'):
                abort(400)
            if target and payload['year'] != target.indicator.plan.year:
                raise ReportError('A published goal’s AOP year cannot change.')
            if target and action == 'publish':
                if str(target.version) != request.form.get('target_version'):
                    raise ReportError('This goal changed. Reload it before publishing.')
                aop.lock_goal(target, target.version)
                period_changed = (target.start_date.isoformat(), target.end_date.isoformat()) != (payload['start_date'], payload['end_date'])
                if period_changed:
                    preview = SimpleNamespace(id=target.id, target_value=target.target_value)
                    from datetime import date
                    preview.start_date = date.fromisoformat(payload['start_date'])
                    preview.end_date = date.fromisoformat(payload['end_date'])
                    children = aop.commitments([target.id])
                    before = aop.progress(target, children)
                    after = aop.progress(preview, children)
                    impact = dict(before=before, after=after,
                                  excluded=[item for item in after['activities'] if item['state'] == 'Outside Goal Period'])
                    from itsdangerous import URLSafeSerializer, BadSignature
                    from flask import current_app
                    signer = URLSafeSerializer(current_app.secret_key, salt='aop-period-review')
                    signature_payload = dict(goal=target.id, version=target.version, payload=payload,
                        completed_before=before['completed'], completed_after=after['completed'],
                        records=[[item['event'].id, str(item['event'].date), str(item['event'].end_date),
                                  item['event'].lifecycle_status] for item in sorted(after['activities'], key=lambda item: item['event'].id)])
                    try:
                        confirmed = signer.loads(request.form.get('impact_token', '')) == signature_payload
                    except BadSignature:
                        confirmed = False
                    impact['token'] = signer.dumps(signature_payload)
                    if not confirmed or request.form.get('confirm_period') != 'yes':
                        return render_template('goals/aop_edit.html', values=values, proposal=proposal,
                                               target=target, error=None, impact=impact)
                aop.claim(target, request.form.get('target_version'))
            if proposal:
                aop.claim(proposal, request.form.get('version'))
            else:
                proposal = AnnualGoalProposal(workflow_kind='director_goal', campus_id=None,
                    proposed_by_id=current_user.id, payload=payload, history=[])
                db.session.add(proposal)
            proposal.payload = payload
            if action == 'publish':
                target = aop.publish(proposal, payload, target)
            else:
                proposal.status = 'draft'
                aop.audit(proposal, 'draft_saved')
            db.session.commit()
            flash('AOP goal published.' if action == 'publish' else 'AOP draft saved.', 'success')
            return redirect(url_for('goals.target_detail', target_id=target.id) if action == 'publish'
                            else url_for('goals.workspace', year=payload['year']))
        except (ReportError, SQLAlchemyError) as exc:
            db.session.rollback()
            error = str(exc) if isinstance(exc, ReportError) else 'The goal could not be saved. No changes were saved; reload and try again.'
            failure_status = 400 if isinstance(exc, (ReportError, IntegrityError)) else 503
    return render_template('goals/aop_edit.html', values=values, proposal=proposal,
                           target=target, error=error, impact=impact,
                           campus_count=campus_query().count()), failure_status if error else 200


def detail(target_id):
    goal = goal_record(target_id)
    children = aop.commitments([goal.id])
    campus_id = current_user.campus_id if current_user.role == 'coordinator' else campus_scope()
    university = aop.progress(goal, children)
    own = aop.progress(goal, children, campus_id) if campus_id else None
    campus_rows = [dict(commitment=child, progress=aop.progress(goal, children, child.campus_id))
                   for child in children if campus_id is None or child.campus_id == campus_id]
    proposals = AnnualGoalProposal.query.filter_by(director_target_id=goal.id, workflow_kind='campus_commitment')
    if current_user.role == 'coordinator':
        proposals = proposals.filter_by(campus_id=current_user.campus_id)
    director_history = AnnualGoalProposal.query.filter_by(published_target_id=goal.id,
                                                         workflow_kind='director_goal').first()
    return render_template('goals/aop_detail.html', goal=goal, university=university, own=own,
                           campus_rows=campus_rows, proposals=proposals.all(), director_history=director_history,
                           today=local_now().date())


@goals_bp.route('/targets/<int:target_id>/commitment', methods=['GET', 'POST'])
@login_required
@roles_required('coordinator')
def commitment(target_id):
    reject_sample_write()
    goal = goal_record(target_id)
    proposal = AnnualGoalProposal.query.filter_by(workflow_kind='campus_commitment',
        director_target_id=goal.id, campus_id=current_user.campus_id).first()
    values = dict(proposal.payload) if proposal else {}
    error = None
    failure_status = 400
    if request.method == 'POST':
        values = request.form.to_dict()
        try:
            if request.form.get('goal_version') != str(goal.version):
                raise ReportError('The Director goal changed. Reload its period and target before submitting.')
            count = aop.activity_count(request.form.get('target_value'))
            note = request.form.get('note', '').strip()
            if len(note) > 4000:
                raise ReportError('Keep your explanation within 4,000 characters.')
            action = request.form.get('action')
            if action not in ('save', 'submit'):
                abort(400)
            # Serialize goal revisions with campus submissions without changing the goal version.
            aop.lock_goal(goal, goal.version)
            if proposal:
                aop.claim(proposal, request.form.get('version'))
            else:
                proposal = AnnualGoalProposal(workflow_kind='campus_commitment', director_target_id=goal.id,
                    campus_id=current_user.campus_id, proposed_by_id=current_user.id, payload={}, history=[])
                db.session.add(proposal)
                db.session.flush()
            proposal.payload = dict(target_value=count, note=note)
            if action == 'submit':
                aop.submit_commitment(proposal, goal, count)
                proposal.submitted_at = db.func.now()
            else:
                proposal.status = 'draft'
                aop.audit(proposal, 'draft_saved')
            db.session.commit()
            flash('Campus commitment submitted. This is now your campus AOP goal.' if action == 'submit' else 'Commitment draft saved.', 'success')
            return redirect(url_for('goals.target_detail', target_id=goal.id))
        except (ReportError, SQLAlchemyError) as exc:
            db.session.rollback()
            error = str(exc) if isinstance(exc, ReportError) else 'The commitment could not be saved. No changes were saved; reload and try again.'
            failure_status = 400 if isinstance(exc, (ReportError, IntegrityError)) else 503
    return render_template('goals/aop_commitment.html', goal=goal, proposal=proposal,
                           values=values, error=error), failure_status if error else 200


@goals_bp.route('/targets/<int:target_id>/link-activities', methods=['GET', 'POST'])
@login_required
@roles_required('coordinator', 'director')
def link_activities(target_id):
    reject_sample_write()
    goal = goal_record(target_id)
    campus_id = current_user.campus_id if current_user.role == 'coordinator' else request.args.get('campus', type=int)
    child = AnnualTarget.query.filter_by(workflow_kind='campus_commitment', director_target_id=goal.id,
                                         campus_id=campus_id, is_active=True).first_or_404()
    proposal = AnnualGoalProposal.query.filter_by(published_target_id=child.id,
                                                  workflow_kind='campus_commitment').one()
    from app.models.annual_plan import AnnualActivityMapping
    linked = {mapping.event_id for mapping in child.activity_mappings}
    query = Event.query.filter_by(campus_id=campus_id).order_by(Event.date.desc(), Event.id.desc())
    pagination = paginate(query)
    error = None
    failure_status = 400
    if request.method == 'POST':
        try:
            if request.form.get('goal_version') != str(goal.version):
                raise ReportError('The goal period changed. Reload before linking activities.')
            aop.lock_goal(goal, goal.version)
            aop.claim(proposal, request.form.get('version'))
            raw_ids = request.form.getlist('event_id')
            if any(not value.isascii() or not value.isdigit() or len(value) > 10 for value in raw_ids):
                raise ReportError('Choose valid activities from this page.')
            ids = [int(value) for value in raw_ids]
            displayed = {event.id: event for event in pagination.items}
            if not set(ids) <= displayed.keys():
                raise ReportError('Choose activities displayed on this page belonging to this campus.')
            for identity in ids:
                if identity not in linked and aop.activity_state(displayed[identity], goal) not in ('Completed', 'Not Yet Completed'):
                    raise ReportError('New links require approved activities wholly within the goal period.')
            for identity, event in displayed.items():
                mapping = AnnualActivityMapping.query.filter_by(target_id=child.id, event_id=identity).first()
                if identity in ids and mapping is None:
                    db.session.add(AnnualActivityMapping(target_id=child.id, event_id=identity))
                    aop.audit(proposal, 'activity_linked', dict(event_id=identity))
                elif identity not in ids and mapping is not None:
                    db.session.delete(mapping)
                    aop.audit(proposal, 'activity_unlinked', dict(event_id=identity))
            db.session.commit()
            flash('Activity links saved. Completed activities update AOP progress automatically.', 'success')
            return redirect(url_for('goals.target_detail', target_id=goal.id))
        except (ReportError, SQLAlchemyError) as exc:
            db.session.rollback()
            error = str(exc) if isinstance(exc, ReportError) else 'Activity links could not be saved. Reload and try again.'
            failure_status = 400 if isinstance(exc, (ReportError, IntegrityError)) else 503
    states = {event.id: aop.activity_state(event, goal) for event in pagination.items}
    return render_template('goals/aop_links.html', goal=goal, child=child, proposal=proposal,
        pagination=pagination, linked=linked, states=states, error=error), failure_status if error else 200
