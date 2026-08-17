"""
Analytics Aggregator for PSU Volunteer Hub
===========================================
Builds aggregate query results used by the director dashboard.
All methods are static — no state, pure aggregation queries.
"""
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import f_oneway
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
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
                results.append(
                    {'campus': campus.name, 'volunteers': 0, 'hours': 0.0})
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
        total_active = User.query.filter(
            User.role == 'volunteer', User._is_active == True).count()
        total_hours = db.session.query(db.func.sum(
            Attendance.hours_completed)).scalar() or 0.0
        total_regs = Registration.query.count()
        completed_regs = Registration.query.filter(
            Registration.status.in_(['confirmed', 'completed'])
        ).count()
        retention_rate = round(
            (completed_regs / total_regs * 100), 1) if total_regs > 0 else 0
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
        rows = db.session.query(User.role, db.func.count(
            User.id)).group_by(User.role).all()
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

    @staticmethod
    def forecast_turnout(campus_id=None):
        """
        Predict expected attendance rate for upcoming events using linear
        regression trained on past events' slots vs. actual attendance rate.

        Returns list of {event, predicted_attendance_rate}.
        """
        past_query = Event.query.filter(Event.date < datetime.now())
        if campus_id:
            past_query = past_query.filter(Event.campus_id == campus_id)
        past_events = past_query.all()

        X_train, y_train = [], []
        for e in past_events:
            total_regs = Registration.query.filter_by(event_id=e.id).count()
            attended = Attendance.query.filter_by(
                event_id=e.id, status='present').count()
            if total_regs > 0:
                X_train.append([e.slots])
                y_train.append(attended / total_regs)

        # Need at least a handful of past events to fit a meaningful line
        if len(X_train) < 3:
            return []

        model = LinearRegression().fit(np.array(X_train), np.array(y_train))

        upcoming_query = Event.query.filter(Event.date >= datetime.now())
        if campus_id:
            upcoming_query = upcoming_query.filter(
                Event.campus_id == campus_id)

        results = []
        for e in upcoming_query.all():
            predicted = float(model.predict([[e.slots]])[0])
            predicted = min(max(predicted, 0.0), 1.0)
            results.append({
                'event': e,
                'predicted_attendance_rate': round(predicted, 3),
            })
        return results

    # Director: cross-campus significance testing

    @staticmethod
    def campus_engagement_significance():
        """
        One-way ANOVA testing whether volunteer engagement (hours
        contributed per volunteer) differs significantly across campuses.

        Returns {f_statistic, p_value, significant, campus_groups}.
        """
        campuses = Campus.query.all()
        groups, campus_names = [], []

        for campus in campuses:
            event_ids = [e.id for e in Event.query.filter_by(
                campus_id=campus.id).all()]
            if not event_ids:
                continue
            rows = db.session.query(
                Attendance.user_id, db.func.sum(Attendance.hours_completed)
            ).filter(Attendance.event_id.in_(event_ids))\
             .group_by(Attendance.user_id).all()
            hours = [h for _, h in rows if h]
            if len(hours) >= 2:
                groups.append(hours)
                campus_names.append(campus.name)

        if len(groups) < 2:
            return {
                'f_statistic': None, 'p_value': None,
                'significant': False, 'campus_groups': campus_names,
            }

        f_stat, p_value = f_oneway(*groups)
        return {
            'f_statistic': round(float(f_stat), 4),
            'p_value': round(float(p_value), 4),
            'significant': bool(p_value < 0.05),
            'campus_groups': campus_names,
        }

    # Director: volunteer engagement segmentation

    @staticmethod
    def volunteer_segments(n_clusters=3):
        """
        Segment volunteers into engagement tiers using K-means clustering
        on total hours, events attended, and recency of last activity.

        Returns list of {user_id, name, cluster, label}.
        """
        volunteers = User.query.filter_by(role='volunteer').all()
        now = datetime.now()

        features, users_ordered = [], []
        for v in volunteers:
            present = [a for a in v.attendance_records if a.status == 'present']
            total_hours = sum(a.hours_completed for a in present)
            events_attended = len(present)
            last_dates = [a.event.date for a in present if a.event]
            recency_days = (now - max(last_dates)).days if last_dates else 365
            features.append([total_hours, events_attended, recency_days])
            users_ordered.append(v)

        if len(features) < n_clusters:
            return []

        X = np.array(features)
        kmeans = KMeans(n_clusters=n_clusters,
                        random_state=42, n_init=10).fit(X)
        labels = kmeans.labels_

        # Rank clusters by average hours so labels are meaningful,
        # not just arbitrary cluster numbers
        avg_hours = {
            c: np.mean([features[i][0]
                       for i in range(len(labels)) if labels[i] == c])
            for c in range(n_clusters)
        }
        ranked = sorted(avg_hours, key=avg_hours.get, reverse=True)
        tier_names = ['Highly Active', 'Occasional', 'At Risk'][:n_clusters]
        cluster_to_label = {cid: tier_names[rank]
                            for rank, cid in enumerate(ranked)}

        return [
            {
                'user_id': user.id,
                'name': user.name,
                'cluster': int(label),
                'label': cluster_to_label[label],
            }
            for user, label in zip(users_ordered, labels)
        ]
