"""
Analytics Aggregator for PSU Volunteer Hub
===========================================
Builds aggregate query results used by the director dashboard.
All methods are static — no state, pure aggregation queries.
"""
from datetime import datetime, timedelta
from app.models import db
from app.models.user import User
from app.models.event import Event, Registration, Attendance, Campus


class AnalyticsAggregator:
    """Produces pre-aggregated data for director analytics views."""

    @staticmethod
    def campus_stats():
        """Return list of {campus, volunteers, hours} per campus sorted by hours desc."""
        campuses = Campus.query.all()
        results = []
        for campus in campuses:
            events = Event.query.filter_by(campus_id=campus.id).all()
            event_ids = [e.id for e in events]
            if not event_ids:
                results.append({'campus': campus.name, 'volunteers': 0, 'hours': 0.0})
                continue
            vol_count = db.session.query(Registration.user_id)\
                .filter(Registration.event_id.in_(event_ids))\
                .distinct().count()
            hours = db.session.query(db.func.sum(Attendance.hours_completed))\
                .filter(Attendance.event_id.in_(event_ids)).scalar() or 0.0
            results.append({
                'campus': campus.name,
                'volunteers': vol_count,
                'hours': round(hours, 1),
            })
        results.sort(key=lambda x: x['hours'], reverse=True)
        return results

    @staticmethod
    def kpi_summary():
        """Return dict of top-level KPIs for the director dashboard."""
        total_active = User.query.filter(User.role == 'volunteer', User._is_active == True).count()
        total_hours = db.session.query(db.func.sum(Attendance.hours_completed)).scalar() or 0.0
        total_regs = Registration.query.count()
        completed_regs = Registration.query.filter(
            Registration.status.in_(['confirmed', 'completed'])
        ).count()
        retention_rate = round((completed_regs / total_regs * 100), 1) if total_regs > 0 else 0
        return {
            'total_active_volunteers': total_active,
            'total_hours': round(total_hours, 1),
            'community_value': round(total_hours * 15, 2),
            'retention_rate': retention_rate,
        }

    @staticmethod
    def trend_data(months=6):
        """Return dict {months, hours, registrations} with monthly breakdown."""
        cutoff = datetime.now() - timedelta(days=30 * months)

        hours_q = db.session.query(
            db.func.strftime('%Y-%m', Event.date).label('month'),
            db.func.sum(Attendance.hours_completed).label('total_hours'),
        ).join(Attendance, Attendance.event_id == Event.id)\
         .filter(Event.date >= cutoff)\
         .group_by('month').order_by('month').all()

        regs_q = db.session.query(
            db.func.strftime('%Y-%m', Event.date).label('month'),
            db.func.count(Registration.id).label('total_regs'),
        ).join(Registration, Registration.event_id == Event.id)\
         .filter(Event.date >= cutoff)\
         .group_by('month').order_by('month').all()

        reg_map = {r.month: r.total_regs for r in regs_q}
        hours_map = {h.month: h.total_hours for h in hours_q}
        all_months = sorted(set(list(reg_map.keys()) + list(hours_map.keys())))

        return {
            'months': all_months,
            'hours': [round(float(hours_map.get(m, 0)), 1) for m in all_months],
            'registrations': [int(reg_map.get(m, 0)) for m in all_months],
        }

    @staticmethod
    def role_demographics():
        """Return dict of {role: count} across all users."""
        rows = db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()
        return {role: count for role, count in rows}

    @staticmethod
    def heatmap_data():
        """Return [{campus: str, value: float}] for campus engagement heatmap."""
        campuses = Campus.query.all()
        data = []
        for campus in campuses:
            events = Event.query.filter_by(campus_id=campus.id).all()
            event_ids = [e.id for e in events]
            if not event_ids:
                data.append({'campus': campus.name, 'value': 0.0})
                continue
            hours = db.session.query(db.func.sum(Attendance.hours_completed))\
                .filter(Attendance.event_id.in_(event_ids)).scalar() or 0.0
            data.append({'campus': campus.name, 'value': round(hours, 1)})
        return data
