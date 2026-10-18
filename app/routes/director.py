"""
Director Routes for PSU Volunteer Hub
========================================
Manages director dashboard and analytics views.
Uses AnalyticsAggregator for all aggregation queries.
"""
import csv
import io
from calendar import Calendar
from datetime import datetime
from flask import Blueprint, render_template, Response, current_app, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import roles_required
from app.recommendation.analytics import AnalyticsAggregator
from app.models import db
from app.models.event import Event, Campus, SdgGoal
from app.models.user import User
from app.dashboard import summarize_report
from app.reports import (
    build_events_report, render_csv, render_pdf, resolve_campus,
    ReportError, _build_meta, parse_date_range)

director_bp = Blueprint('director', __name__, url_prefix='')


def _historical_filters():
    return {
        'campus_id': request.args.get('campus_id', type=int),
        'start_year': request.args.get('start_year', type=int),
        'end_year': request.args.get('end_year', type=int),
        'activity_type': request.args.get('activity_type', '').strip() or None,
    }


@director_bp.route('/director_dash')
@login_required
@roles_required('director', 'admin')
def director_dash():
    campus_stats = AnalyticsAggregator.historical_campus_stats()
    total_volunteers = sum(c['participations'] for c in campus_stats)
    total_activities = sum(c['activities'] for c in campus_stats)
    top_campuses = campus_stats[:3]
    live_summary = AnalyticsAggregator.participation_summary()
    live_campuses = AnalyticsAggregator.campus_comparison()
    accomplishments = AnalyticsAggregator.activity_accomplishments(limit=5)
    return render_template('director/Director_Dash.html',
                           campus_stats=campus_stats,
                           total_volunteers=total_volunteers,
                           total_activities=total_activities,
                           top_campuses=top_campuses,
                           live_summary=live_summary,
                           live_campuses=live_campuses,
                           accomplishments=accomplishments)


@director_bp.route('/director/calendar')
@login_required
@roles_required('director', 'admin')
def activity_calendar():
    now = datetime.now()
    year = request.args.get('year', now.year, type=int) or now.year
    month = request.args.get('month', now.month, type=int) or now.month
    campus_id = resolve_campus(request.args.get('campus_id'))
    category = request.args.get('category', '').strip()
    if not 1 <= month <= 12:
        year, month = now.year, now.month
    query = Event.query.filter(db.extract('year', Event.date) == year,
                               db.extract('month', Event.date) == month)
    if campus_id:
        query = query.filter(Event.campus_id == campus_id)
    if category:
        query = query.filter(Event.category == category)
    by_day = {}
    for event in query.order_by(Event.date).all():
        by_day.setdefault(event.date.day, []).append(event)
    previous = (year - 1, 12) if month == 1 else (year, month - 1)
    following = (year + 1, 1) if month == 12 else (year, month + 1)
    categories = [row[0] for row in db.session.query(Event.category).filter(
        Event.category.isnot(None)).distinct().order_by(Event.category).all()]
    return render_template('director/activity_calendar.html',
                           calendar_weeks=Calendar(firstweekday=0).monthdayscalendar(year, month),
                           calendar_events=by_day, calendar_month=datetime(year, month, 1).strftime('%B %Y'),
                           calendar_year=year, calendar_number=month,
                           previous_calendar=previous, next_calendar=following,
                           campuses=Campus.query.order_by(Campus.name).all(), categories=categories,
                           selected_campus=campus_id, selected_category=category)


@director_bp.route('/analytics')
@login_required
@roles_required('director', 'admin')
def analytics():
    try:
        parse_date_range(request.args.get('start_date'), request.args.get('end_date'))
    except ReportError:
        flash('Use valid report dates, with the start date on or before the end date.', 'error')
        return redirect(url_for('director.analytics'))
    filters = _historical_filters()
    demographics = AnalyticsAggregator.role_demographics()
    historical_summary = AnalyticsAggregator.historical_summary(**filters)
    historical_campus_data = AnalyticsAggregator.historical_campus_stats(**filters)
    from app.models.event import HistoricalActivity
    campuses = Campus.query.order_by(Campus.name).all()
    activity_types = [row[0] for row in db.session.query(
        HistoricalActivity.activity_type).filter(
            HistoricalActivity.activity_type.isnot(None)).distinct().all()]

    # Live event-based report (date / campus / category filters)
    live_campus = resolve_campus(request.args.get('campus_id'))
    live_start = request.args.get('start_date', '').strip()
    live_end = request.args.get('end_date', '').strip()
    live_category = request.args.get('category', '').strip()
    live_sex = request.args.get('sex', '').strip().lower()
    live_sex = live_sex if live_sex in (
        'male', 'female', 'prefer_not_to_say', 'unrecorded') else None
    live_sdg_id = request.args.get('sdg_id', type=int)
    if live_sdg_id and db.session.get(SdgGoal, live_sdg_id) is None:
        live_sdg_id = None
    try:
        live_rows, live_summary = build_events_report(
            campus_id=live_campus, start_date=live_start,
            end_date=live_end, category=live_category, sex=live_sex,
            sdg_id=live_sdg_id)
    except ReportError:
        live_rows, live_summary = [], {
            'event_count': 0, 'total_registrations': 0,
            'total_attended': 0, 'total_completed': 0,
            'total_psu': 0, 'total_external': 0}
        flash('Use a valid date range for the activity report.', 'error')
    dashboard_data = summarize_report(live_rows)
    report_page = max(request.args.get('page', 1, type=int), 1)
    report_page_size = 10
    report_total_pages = max(1, (len(live_rows) + report_page_size - 1) // report_page_size)
    report_page = min(report_page, report_total_pages)
    report_rows = live_rows[(report_page - 1) * report_page_size:report_page * report_page_size]
    categories = [row[0] for row in db.session.query(Event.category).filter(
        Event.category.isnot(None)).distinct().order_by(Event.category).all()]
    department = request.args.get('department', '').strip()
    selected_campus_id = request.args.get('campus_id', type=int)
    department_query = db.session.query(User.college_affiliation).filter(
        User.college_affiliation.isnot(None))
    if selected_campus_id:
        department_query = department_query.filter(User.campus_id == selected_campus_id)
    departments = [row[0] for row in department_query.distinct().order_by(
        User.college_affiliation).all()]

    # Supplementary profile evidence retains its independently labelled scope.
    live_campus_filter = live_campus
    top_skills = AnalyticsAggregator.skill_distribution(limit=8)
    top_interests = AnalyticsAggregator.interest_distribution(limit=8)
    department_participants = AnalyticsAggregator.department_participants(
        campus_id=live_campus_filter, department=department or None)
    sex_participation = AnalyticsAggregator.sex_participation(
        campus_id=live_campus_filter, start_date=live_start, end_date=live_end,
        category=live_category, sex=live_sex)
    award_years = sorted({event.date.year for event in Event.query.with_entities(Event.date).all()}, reverse=True)
    award_year = request.args.get('award_year', type=int)
    if award_year not in award_years:
        award_year = award_years[0] if award_years else datetime.now().year
    leaderboards = (AnalyticsAggregator.award_leaderboards(award_year)
                    if current_user.role == 'director' else None)

    return render_template('director/Director_impact_anlaytics_dash.html',
                            demographics=demographics,
                            historical_summary=historical_summary,
                            historical_campus_data=historical_campus_data,
                            campuses=campuses, activity_types=activity_types,
                            categories=categories,
                            sdgs=SdgGoal.query.order_by(SdgGoal.number).all(),
                            selected_sex=live_sex, selected_sdg_id=live_sdg_id,
                            selected_filters=filters,
                            live_rows=report_rows, live_summary=live_summary,
                            dashboard_data=dashboard_data,
                            report_page=report_page, report_total_pages=report_total_pages,
                            top_skills=top_skills,
                            top_interests=top_interests,
                            departments=departments, selected_department=department,
                            department_participants=department_participants,
                            sex_participation=sex_participation,
                            award_years=award_years, award_year=award_year,
                            leaderboards=leaderboards)


@director_bp.route('/reports/campus.csv')
@login_required
@roles_required('director', 'admin')
def export_campus_csv():
    filters = _historical_filters()
    data = AnalyticsAggregator.historical_campus_stats(**filters)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Campus / Unit', 'Activities', 'Volunteer Participations',
                     'Incomplete Source Rows'])
    for row in data:
        writer.writerow([row['campus'], row['activities'],
                         row['participations'], row['incomplete_records']])
    return Response(output.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition':
        'attachment;filename=psu_historical_campus_participation.csv'})


@director_bp.route('/reports/campus.pdf')
@login_required
@roles_required('director', 'admin')
def export_campus_pdf():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, Image)

    filters = _historical_filters()
    data = AnalyticsAggregator.historical_campus_stats(**filters)
    summary = AnalyticsAggregator.historical_summary(**filters)
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=landscape(A4), rightMargin=18 * mm,
        leftMargin=18 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        title='PSU Historical Campus Participation Report')
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle', parent=styles['Title'], textColor=colors.HexColor('#00408B'),
        fontSize=18, leading=21, alignment=TA_CENTER, spaceAfter=2 * mm)
    subtitle_style = ParagraphStyle(
        'ReportSubtitle', parent=styles['BodyText'], alignment=TA_CENTER,
        textColor=colors.HexColor('#4D596A'), spaceAfter=3 * mm)
    story = []
    logo_path = current_app.static_folder + '/assets/PSU-logo.png'
    story.append(Image(logo_path, width=14 * mm, height=14 * mm))
    story.append(Paragraph('PSU Historical Campus Participation', title_style))
    story.append(Paragraph(
        'Summary of Volunteer Activities, CY 2020–2025 · '
        f'Generated {datetime.now().strftime("%B %d, %Y")}', subtitle_style))
    story.append(Paragraph(
        f'<b>{summary["activities"]}</b> activity records &nbsp;&nbsp;·&nbsp;&nbsp; '
        f'<b>{summary["volunteer_participations"]:,}</b> volunteer participations '
        f'&nbsp;&nbsp;·&nbsp;&nbsp; <b>{summary["incomplete_records"]}</b> incomplete source rows',
        styles['BodyText']))
    story.append(Spacer(1, 3 * mm))
    table_data = [['Campus / Unit', 'Activities', 'Volunteer Participations',
                   'Incomplete Source Rows']]
    table_data.extend([[row['campus'], f"{row['activities']:,}",
                        f"{row['participations']:,}",
                        f"{row['incomplete_records']:,}"] for row in data])
    table = Table(table_data, colWidths=[105 * mm, 37 * mm, 55 * mm, 50 * mm],
                  repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00408B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F3F6FC')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#B8C2D1')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, Spacer(1, 3 * mm), Paragraph(
        'Note: Participations are aggregate entries from the source report and '
        'must not be interpreted as unique volunteer accounts. Missing values '
        'were retained rather than estimated.', styles['BodyText'])])
    document.build(story)
    return Response(output.getvalue(), mimetype='application/pdf', headers={
        'Content-Disposition':
        'attachment;filename=psu_historical_campus_participation.pdf'})


# ── Live, event-based university reporting (Director + Admin) ──────────────────

def _report_scope_label(campus_id):
    if campus_id is None:
        return 'All Campuses'
    campus = db.session.get(Campus, campus_id)
    return f'{campus.name} Campus' if campus else 'All Campuses'


def _university_report_payload():
    """Build the filtered dataset for the live university report.

    Returns (rows, summary, meta, error). Authorization: directors and admins
    may request any single campus or all campuses; the campus is validated and
    never trusted blindly. Invalid dates raise ReportError -> caller redirects.
    """
    campus_id = resolve_campus(request.args.get('campus_id'))
    start = request.args.get('start_date', '').strip()
    end = request.args.get('end_date', '').strip()
    category = request.args.get('category', '').strip()
    sex = request.args.get('sex', '').strip().lower()
    sdg_id = request.args.get('sdg_id', type=int)
    sdg = db.session.get(SdgGoal, sdg_id) if sdg_id else None
    rows, summary = build_events_report(
        campus_id=campus_id, start_date=start, end_date=end,
        category=category, sex=sex if sex in (
            'male', 'female', 'prefer_not_to_say', 'unrecorded') else None,
        sdg_id=sdg.id if sdg else None)
    scope = _report_scope_label(campus_id)
    role_label = 'Administration' if current_user.role == 'admin' else 'Director'
    meta = _build_meta(
        title='University-wide Activity Report', scope=scope,
        start_date=start, end_date=end, category=category,
        role_label=role_label)
    return rows, summary, meta


@director_bp.route('/reports/university.csv')
@login_required
@roles_required('director', 'admin')
def export_university_csv():
    try:
        rows, summary, meta = _university_report_payload()
    except ReportError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('director.analytics'))
    csv_data = render_csv(rows, summary, meta)
    return Response(csv_data, mimetype='text/csv', headers={
        'Content-Disposition':
        'attachment;filename=psu_university_activity.csv'})


@director_bp.route('/reports/university.pdf')
@login_required
@roles_required('director', 'admin')
def export_university_pdf():
    try:
        rows, summary, meta = _university_report_payload()
    except ReportError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('director.analytics'))
    pdf_data = render_pdf(rows, summary, meta)
    return Response(pdf_data, mimetype='application/pdf', headers={
        'Content-Disposition':
        'attachment;filename=psu_university_activity.pdf'})
