"""
Director Routes for PSU Volunteer Hub
========================================
Manages director dashboard and analytics views.
Uses AnalyticsAggregator for all aggregation queries.
"""
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, Response, current_app
from flask_login import login_required
from app.utils.decorators import coordinator_or_above
from app.recommendation.analytics import AnalyticsAggregator

director_bp = Blueprint('director', __name__, url_prefix='')


@director_bp.route('/director_dash')
@login_required
@coordinator_or_above()
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
@coordinator_or_above()
def analytics():
    kpi_cards = AnalyticsAggregator.kpi_summary()
    campus_data = AnalyticsAggregator.campus_stats()
    demographics = AnalyticsAggregator.role_demographics()
    trend_data = AnalyticsAggregator.trend_data()
    heatmap_data = AnalyticsAggregator.heatmap_data()
    historical_summary = AnalyticsAggregator.historical_summary()
    historical_campus_data = AnalyticsAggregator.historical_campus_stats()
    return render_template('director/Director_impact_anlaytics_dash.html',
                           kpi_cards=kpi_cards,
                           campus_data=campus_data,
                           demographics=demographics,
                           trend_data=trend_data,
                           heatmap_data=heatmap_data,
                           historical_summary=historical_summary,
                           historical_campus_data=historical_campus_data)


@director_bp.route('/reports/campus.csv')
@login_required
@coordinator_or_above()
def export_campus_csv():
    data = AnalyticsAggregator.historical_campus_stats()
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
@coordinator_or_above()
def export_campus_pdf():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, Image)

    data = AnalyticsAggregator.historical_campus_stats()
    summary = AnalyticsAggregator.historical_summary()
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
