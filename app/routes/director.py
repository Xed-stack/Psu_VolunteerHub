"""
Director Routes for PSU Volunteer Hub
========================================
Manages director dashboard and analytics views.
Uses AnalyticsAggregator for all aggregation queries.
"""
import csv
import io
from flask import Blueprint, render_template, Response
from flask_login import login_required
from app.utils.decorators import coordinator_or_above
from app.recommendation.analytics import AnalyticsAggregator

director_bp = Blueprint('director', __name__, url_prefix='')


@director_bp.route('/director_dash')
@login_required
@coordinator_or_above()
def director_dash():
    campus_stats = AnalyticsAggregator.campus_stats()
    total_volunteers = sum(c['volunteers'] for c in campus_stats)
    total_hours = sum(c['hours'] for c in campus_stats)
    top_campuses = campus_stats[:3]
    trends = {'volunteer_growth': 12.5, 'hours_growth': 8.3, 'events_growth': 15.0}
    return render_template('Director_Dash.html',
                           campus_stats=campus_stats,
                           total_volunteers=total_volunteers,
                           total_hours=round(total_hours, 1),
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
    return render_template('Director_impact_anlaytics_dash.html',
                           kpi_cards=kpi_cards,
                           campus_data=campus_data,
                           demographics=demographics,
                           trend_data=trend_data,
                           heatmap_data=heatmap_data)


@director_bp.route('/reports/campus.csv')
@login_required
@coordinator_or_above()
def export_campus_csv():
    data = AnalyticsAggregator.campus_stats()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Campus', 'Volunteers', 'Hours'])
    for row in data:
        writer.writerow([row['campus'], row['volunteers'], row['hours']])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=campus_report.csv'})
