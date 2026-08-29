"""
Director Routes for PSU Volunteer Hub
========================================
Manages director dashboard and analytics views.
Uses AnalyticsAggregator for all aggregation queries.
"""
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, Response, current_app, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import roles_required
from app.recommendation.analytics import AnalyticsAggregator
from app.models import db
from app.models.event import Event, Campus
from app.reports import (
    build_events_report, render_csv, render_pdf, resolve_campus,
    ReportError, _build_meta)

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
    trends = {'volunteer_growth': 12.5,
              'hours_growth': 8.3, 'events_growth': 15.0}
    return render_template('director/Director_Dash.html',
                           campus_stats=campus_stats,
                           total_volunteers=total_volunteers,
                           total_activities=total_activities,
                           trends=trends,
                           top_campuses=top_campuses)


@director_bp.route('/analytics')
@login_required
@roles_required('director', 'admin')
def analytics():
    filters = _historical_filters()
    kpi_cards = AnalyticsAggregator.kpi_summary()
    campus_data = AnalyticsAggregator.campus_stats()
    demographics = AnalyticsAggregator.role_demographics()
    trend_data = AnalyticsAggregator.trend_data()
    heatmap_data = AnalyticsAggregator.heatmap_data()
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
    try:
        live_rows, live_summary = build_events_report(
            campus_id=live_campus, start_date=live_start,
            end_date=live_end, category=live_category)
    except ReportError:
        live_rows, live_summary = [], {
            'event_count': 0, 'total_registrations': 0,
            'total_attended': 0, 'total_completed': 0, 'total_hours': 0.0}
    categories = [row[0] for row in db.session.query(Event.category).filter(
        Event.category.isnot(None)).distinct().order_by(Event.category).all()]

    # Phase 18: centralized descriptive analytics (university-wide for Director/Admin).
    live_campus_filter = live_campus
    participation = AnalyticsAggregator.participation_summary(
        campus_id=live_campus_filter, start_date=live_start, end_date=live_end,
        category=live_category)
    campus_comparison = AnalyticsAggregator.campus_comparison()
    category_breakdown = AnalyticsAggregator.category_distribution(
        campus_id=live_campus_filter, start_date=live_start, end_date=live_end)
    activity_breakdown = AnalyticsAggregator.activity_performance(
        campus_id=live_campus_filter, start_date=live_start, end_date=live_end,
        category=live_category)
    monthly = AnalyticsAggregator.monthly_engagement(
        campus_id=live_campus_filter)
    weekly = AnalyticsAggregator.weekly_engagement(
        campus_id=live_campus_filter)
    type_split = AnalyticsAggregator.psu_vs_outsider(
        campus_id=live_campus_filter, start_date=live_start, end_date=live_end,
        category=live_category)
    top_skills = AnalyticsAggregator.skill_distribution(limit=8)
    top_interests = AnalyticsAggregator.interest_distribution(limit=8)

    return render_template('director/Director_impact_anlaytics_dash.html',
                            kpi_cards=kpi_cards,
                            campus_data=campus_data,
                            demographics=demographics,
                            trend_data=trend_data,
                            heatmap_data=heatmap_data,
                            historical_summary=historical_summary,
                            historical_campus_data=historical_campus_data,
                            campuses=campuses, activity_types=activity_types,
                            selected_filters=filters,
                            live_rows=live_rows, live_summary=live_summary,
                            participation=participation,
                            campus_comparison=campus_comparison,
                            category_breakdown=category_breakdown,
                            activity_breakdown=activity_breakdown,
                            monthly=monthly,
                            weekly=weekly,
                            type_split=type_split,
                            top_skills=top_skills,
                            top_interests=top_interests)


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
    rows, summary = build_events_report(
        campus_id=campus_id, start_date=start, end_date=end,
        category=category)
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
