"""Annual history, existing goal URLs, and shared AOP presentation helpers."""
import csv
import io
from datetime import datetime
from math import ceil
from xml.sax.saxutils import escape

from flask import Blueprint, abort, flash, redirect, render_template, request, Response, url_for
from flask_login import login_required, current_user
from app.services.activity_workflow import local_now
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.pagination import paginate

from app.models import db
from app.campuses import campus_query
from app.models.annual_plan import (AnnualPlan, AnnualIndicator, AnnualTarget,
                                   AnnualActivityMapping, AnnualGoalProposal)
from app.models.event import Campus, Event
from app.utils.decorators import roles_required
from app.annual_goals import (summary, comparisons, validate_definition, selected_year,
                              number, RULES, BASES, cutoff_for)
from app.reports import ReportError, csv_safe

goals_bp = Blueprint('goals', __name__, url_prefix='/annual-goals')


@goals_bp.app_template_filter('goal_number')
def goal_number(value):
    """Format validated goal numbers without trailing decimal zeros; preserve unknowns."""
    if value is None:
        return 'Not available'
    text = format(number(value), 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def director():
    """Check exact director role; read-capable admins are not goal publishers here."""
    return current_user.role == 'director'


def campus_scope():
    """Resolve reader scope without accepting a coordinator's requested campus.

    Director/admin may choose an existing campus or separate university targets.
    Coordinators always use assigned campus; missing assignment returns 403.
    """
    if current_user.role in ('director', 'admin'):
        value = request.args.get('campus', '')
        if not value:
            return None
        try:
            campus = db.session.get(Campus, int(value))
        except ValueError:
            campus = None
        if campus is None:
            abort(400, description='Choose an available campus.')
        return campus.id
    if current_user.campus_id is None:
        abort(403)
    return current_user.campus_id


def reject_sample_write():
    """Reject sample=1 on query/form so preview data cannot become official writes."""
    if request.args.get('sample') == '1' or request.form.get('sample') == '1':
        abort(400, description='Sample previews are read-only. Exit the preview to manage official goals.')


def owned_proposal(proposal_id, lock=False):
    """Load proposal or 404; restrict non-directors to their assigned campus.

    Mutation callers request a row lock to serialize edits and review decisions
    on databases supporting FOR UPDATE. Route decorators enforce allowed roles.
    """
    statement = select(AnnualGoalProposal).where(AnnualGoalProposal.id == proposal_id)
    if lock:
        statement = statement.with_for_update()
    proposal = db.session.execute(statement).scalar_one_or_none()
    if proposal is None:
        abort(404)
    if not director() and (current_user.campus_id is None or proposal.campus_id != current_user.campus_id):
        abort(403)
    return proposal


@goals_bp.route('')
@login_required
@roles_required('coordinator', 'director', 'admin')
def details():
    """Show approved goal results with scoped filters and ten rows per page.

    Export all filtered rows before pagination. Block official exports of sample
    figures. Participation basis affects demographic counts, not target evidence.
    Campus comparison cards recalculate plan/program/office selections separately;
    status filtering applies to main detail rows.
    """
    try:
        year = selected_year(request.args.get('year'))
    except ReportError as exc:
        abort(400, description=str(exc))
    if request.args.get('plan') == 'ASP':
        abort(410, description='ASP has been retired.')
    if request.args.get('history') != '1':
        from app.routes.aop import index
        return index()
    campus_id = campus_scope()
    sample = request.args.get('sample') == '1'
    plan = summary(year, campus_id, sample, historical=True)
    rows = plan['rows']
    filters = {key: request.args.get(key, '').strip() for key in ('plan', 'program', 'office', 'status')}
    if filters['plan'] not in ('', 'AOP') or filters['status'] not in ('', 'met', 'remaining', 'pending'):
        abort(400, description='Choose valid goal filters.')
    programs = sorted({row['program'] for row in rows})
    offices = sorted({row['responsible_office'] for row in rows})
    for key, field in [('program', 'program'), ('office', 'responsible_office')]:
        if filters[key]:
            rows = [row for row in rows if row[field] == filters[key]]
    if filters['plan']:
        rows = [row for row in rows if filters['plan'] in row['plan_types']]
    if filters['status']:
        rows = [row for row in rows if (row['met'] if filters['status'] == 'met' else row['pending'] if filters['status'] == 'pending' else row['verified'] and not row['met'])]
    basis = request.args.get('basis', 'verified_attendance')
    if basis not in ('registrations', 'verified_attendance', 'completed', 'unique_attendees'):
        abort(400, description='Choose a valid participation counting basis.')
    export = request.args.get('export')
    if export:
        if sample:
            abort(400, description='Sample figures cannot be exported as official results.')
        return export_rows(rows, plan, filters, export)
    pages = max(1, ceil(len(rows) / 10))
    page = min(max(request.args.get('page', 1, type=int), 1), pages)
    query = request.args.to_dict()
    query.pop('page', None)
    university_reader = current_user.role in ('director', 'admin')
    campus_rows = comparisons(year, sample, historical=True) if university_reader else []
    # Campus cards apply plan/program/office filters; main rows also apply status.
    from app.annual_goals import summarize
    for campus in campus_rows:
        selected = [row for row in campus['rows']
                    if (not filters['plan'] or filters['plan'] in row['plan_types'])
                    and (not filters['program'] or row['program'] == filters['program'])
                    and (not filters['office'] or row['responsible_office'] == filters['office'])]
        updated = summarize(selected, year, campus['campus_id'], sample)
        campus.update(updated)
    return render_template('goals/details.html', plan=plan, rows=rows[(page-1)*10:page*10],
        row_count=len(rows), page=page, pages=pages, query=query, filters=filters, programs=programs,
        offices=offices, campuses=campus_query().order_by(Campus.name).all() if university_reader else [],
        campus_rows=campus_rows, basis=basis,
        director=university_reader, sample=sample, campus_id=campus_id,
        scope_name=(db.session.get(Campus, campus_id).name + ' campus') if campus_id is not None else 'University')


@goals_bp.route('/targets/<int:target_id>')
@login_required
@roles_required('coordinator', 'director', 'admin')
def target_detail(target_id):
    """Resolve a member through the merged approved obligation, preserving conflicts."""
    if request.args.get('sample') == '1':
        abort(400, description='Sample indicators do not have official evidence records.')
    target = db.get_or_404(AnnualTarget, target_id)
    if target.workflow_kind != 'legacy':
        from app.routes.aop import detail
        return detail(target_id)
    if current_user.role == 'coordinator' and (current_user.campus_id is None or target.campus_id != current_user.campus_id):
        abort(403)
    if not target.is_active or target.indicator.plan.status != 'approved':
        abort(404)
    year = target.indicator.plan.year
    plan = summary(year, target.campus_id, historical=True)
    key = target.indicator.shared_key
    row = next((row for row in plan['rows'] if (row['shared_key'] == key if key else row['target_id'] == target.id)), None)
    if row is None:
        abort(404)
    members = AnnualTarget.query.join(AnnualIndicator).join(AnnualPlan).filter(
        AnnualTarget.workflow_kind == 'legacy', AnnualPlan.plan_type == 'AOP',
        AnnualPlan.year == year, AnnualPlan.status == 'approved', AnnualTarget.is_active.is_(True),
        AnnualTarget.campus_id == target.campus_id,
        AnnualIndicator.shared_key == key if key else AnnualTarget.id == target.id
    ).options(joinedload(AnnualTarget.indicator).joinedload(AnnualIndicator.plan),
              joinedload(AnnualTarget.results)).order_by(AnnualTarget.id).all()
    return render_template('goals/target_detail.html', target=target, row=row, plan=plan,
                           members=members, director=director(), sample=False)


def export_rows(rows, plan, filters, kind):
    """Format supplied goal evidence as CSV/PDF with source, coverage, and scope.

    Export caller's full filtered set, not page slice. Protect spreadsheet text
    with csv_safe and escape PDF Paragraph text; reject unsupported formats.
    """
    if kind not in ('csv', 'pdf'):
        abort(400)
    columns = ['Start Date', 'End Date', 'Code', 'Indicator', 'Plans', 'Program', 'Actual', 'Target', 'Unit', 'Rule', 'Office', 'Status', 'Source', 'Coverage']
    data = [[row.get('start_date', ''), row.get('end_date', ''), row['code'], row['name'], '/'.join(row['plan_types']), row['program'],
             row['actual'] if row['verified'] else 'Not available', row['target'], row['unit'],
             row['rule_label'], row['responsible_office'], row['status'], row['source_document'], row['coverage_note'] or ''] for row in rows]
    scope = f"{plan['scope']} targets; campus={plan['campus_id'] or 'university'}; year={plan['year']}; cutoff={plan['cutoff']}; filters={filters}"
    if kind == 'csv':
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['Annual goal evidence', csv_safe(scope)])
        writer.writerow(columns)
        writer.writerows([[csv_safe(value) for value in record] for record in data])
        body, mime = stream.getvalue(), 'text/csv'
    else:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import A4
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        story = [Paragraph('Annual goal evidence', styles['Title']), Paragraph(escape(scope), styles['BodyText'])]
        for record in data:
            story.extend([Spacer(1, 14), Paragraph(escape(str(record[2]) + ': ' + str(record[3])), styles['Heading2'])])
            for label, value in zip(columns, record):
                story.append(Paragraph(escape(f'{label}: {value}'), styles['BodyText']))
        if not data:
            story.append(Paragraph('No approved targets match these filters.', styles['BodyText']))
        SimpleDocTemplate(buffer, pagesize=A4).build(story)
        body, mime = buffer.getvalue(), 'application/pdf'
    return Response(body, mimetype=mime, headers={'Content-Disposition': f'attachment; filename=annual-goals-{plan["year"]}.{kind}'})


@goals_bp.route('/workspace')
@login_required
@roles_required('coordinator', 'director')
def workspace():
    from app.routes.aop import index
    return index()


@goals_bp.route('/proposals/new', methods=['GET', 'POST'])
@goals_bp.route('/proposals/<int:proposal_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('coordinator', 'director')
def edit(proposal_id=None):
    from app.routes.aop import edit_goal
    return edit_goal(proposal_id)


@goals_bp.route('/proposals/<int:proposal_id>', methods=['GET', 'POST'])
@login_required
@roles_required('coordinator', 'director')
def review(proposal_id):
    proposal = owned_proposal(proposal_id)
    if request.method == 'POST':
        abort(409, description='Historical records are read-only. Campus commitments do not require approval.')
    if proposal.workflow_kind != 'legacy':
        identity = proposal.director_target_id or proposal.published_target_id
        if identity:
            return redirect(url_for('goals.target_detail', target_id=identity))
        return redirect(url_for('goals.edit', proposal_id=proposal.id))
    return render_template('goals/review.html', proposal=proposal, director=False,
                           error=None, rules=RULES, bases=BASES)


@goals_bp.route('/targets/<int:target_id>/activities')
@login_required
@roles_required('coordinator', 'director', 'admin')
def target_activities(target_id):
    """Show paginated mapped activities in target year and campus scope.

    Coordinators must own target campus. Listing includes upcoming mappings;
    target assessment separately checks cutoff, ended state, and attendance.
    """
    target = db.get_or_404(AnnualTarget, target_id)
    if current_user.role == 'coordinator' and (current_user.campus_id is None or target.campus_id != current_user.campus_id):
        abort(403)
    year = target.indicator.plan.year
    query = Event.query.join(AnnualActivityMapping).filter(
        AnnualActivityMapping.target_id == target.id,
        Event.date >= datetime(year, 1, 1), Event.date < datetime(year+1, 1, 1))
    if target.campus_id is not None:
        query = query.filter(Event.campus_id == target.campus_id)
    pagination = paginate(query.options(joinedload(Event.campus)).order_by(Event.date.desc(), Event.id.desc()))
    return render_template('goals/activities.html', target=target, pagination=pagination,
                           activities=pagination.items, year=year)


@goals_bp.route('/targets/<int:target_id>/evidence', methods=['GET', 'POST'])
@login_required
@roles_required('director')
def evidence(target_id):
    if request.method == 'POST':
        abort(409, description='Historical AOP evidence is read-only.')
    return redirect(url_for('goals.target_detail', target_id=target_id))


# Register the dated AOP routes after the shared blueprint and helpers exist.
from app.routes import aop as _aop_routes
