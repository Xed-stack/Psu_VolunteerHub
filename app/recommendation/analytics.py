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
from app.models.event import (Event, Registration, Attendance, Campus,
                              HistoricalActivity)


class AnalyticsAggregator:
    """Produces pre-aggregated data for director analytics views."""

    @staticmethod
    def historical_summary(campus_id=None):
        """Return aggregate counts imported from audited legacy reports."""
        query = HistoricalActivity.query
        volunteer_query = db.session.query(
            db.func.sum(HistoricalActivity.volunteer_count))
        if campus_id:
            query = query.filter_by(campus_id=campus_id)
            volunteer_query = volunteer_query.filter(
                HistoricalActivity.campus_id == campus_id)
        return {
            'activities': query.count(),
            'volunteer_participations': int(volunteer_query.scalar() or 0),
            'years_covered': query.with_entities(
                HistoricalActivity.year_conducted)
                .filter(HistoricalActivity.year_conducted.isnot(None))
                .distinct().count(),
            'incomplete_records': query.filter(db.or_(
                HistoricalActivity.year_conducted.is_(None),
                HistoricalActivity.volunteer_count.is_(None))).count(),
        }

    @staticmethod
    def historical_campus_stats(campus_id=None):
        """Return aggregate activity and participation totals by reporting unit."""
        query = db.session.query(
            HistoricalActivity.unit_name,
            db.func.count(HistoricalActivity.id),
            db.func.sum(HistoricalActivity.volunteer_count),
            db.func.sum(db.case((db.or_(
                HistoricalActivity.year_conducted.is_(None),
                HistoricalActivity.volunteer_count.is_(None)), 1), else_=0)),
        )
        if campus_id:
            query = query.filter(HistoricalActivity.campus_id == campus_id)
        rows = query.group_by(HistoricalActivity.unit_name).all()
        results = [{
            'campus': unit,
            'activities': int(activities),
            'participations': int(participations or 0),
            'incomplete_records': int(incomplete or 0),
        } for unit, activities, participations, incomplete in rows]
        results.sort(key=lambda row: row['participations'], reverse=True)
        return results

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
    def kpi_summary(campus_id=None):
        """Return dict of top-level KPIs, optionally scoped to one campus."""
        user_query = User.query.filter(
            User.role == 'volunteer', User._is_active == True)
        if campus_id:
            user_query = user_query.filter(User.campus_id == campus_id)
        total_active = user_query.count()

        if campus_id:
            event_ids = [e.id for e in Event.query.filter_by(
                campus_id=campus_id).all()]
            hours_q = db.session.query(db.func.sum(Attendance.hours_completed))
            total_hours = hours_q.filter(Attendance.event_id.in_(
                event_ids)).scalar() or 0.0 if event_ids else 0.0
            reg_q = Registration.query.filter(Registration.event_id.in_(
                event_ids)) if event_ids else Registration.query.filter(False)
        else:
            total_hours = db.session.query(db.func.sum(
                Attendance.hours_completed)).scalar() or 0.0
            reg_q = Registration.query

        total_regs = reg_q.count()
        completed_regs = reg_q.filter(
            Registration.status.in_(['confirmed', 'completed'])).count()
        retention_rate = round(
            (completed_regs / total_regs * 100), 1) if total_regs > 0 else 0

        return {
            'total_active_volunteers': total_active,
            'total_hours': round(total_hours, 1),
            'retention_rate': retention_rate,
        }

    @staticmethod
    def trend_data(months=6, campus_id=None):
        """Return dict {months, hours, registrations}, optionally scoped to one campus."""
        cutoff = datetime.now() - timedelta(days=30 * months)

        hours_query = db.session.query(Event.date, Attendance.hours_completed)\
            .join(Attendance, Attendance.event_id == Event.id)\
            .filter(Event.date >= cutoff)
        reg_query = db.session.query(Event.date)\
            .join(Registration, Registration.event_id == Event.id)\
            .filter(Event.date >= cutoff)

        if campus_id:
            hours_query = hours_query.filter(Event.campus_id == campus_id)
            reg_query = reg_query.filter(Event.campus_id == campus_id)

        hours_rows = hours_query.all()
        reg_rows = reg_query.all()

        hours_map = {}
        for event_date, hours in hours_rows:
            key = event_date.strftime('%Y-%m')
            hours_map[key] = hours_map.get(key, 0.0) + (hours or 0.0)

        reg_map = {}
        for (event_date,) in reg_rows:
            key = event_date.strftime('%Y-%m')
            reg_map[key] = reg_map.get(key, 0) + 1

        all_months = sorted(set(list(reg_map.keys()) + list(hours_map.keys())))
        return {
            'months': all_months,
            'hours': [round(float(hours_map.get(m, 0)), 1) for m in all_months],
            'registrations': [int(reg_map.get(m, 0)) for m in all_months],
        }

    @staticmethod
    def attendance_summary(campus_id=None, limit=10):
        """Return [{event, registered, attended, rate}] for completed/upcoming events."""
        event_query = Event.query
        if campus_id:
            event_query = event_query.filter_by(campus_id=campus_id)
        events = event_query.order_by(Event.date.desc()).limit(limit).all()

        results = []
        for e in events:
            registered = Registration.query.filter_by(event_id=e.id).count()
            attended = Attendance.query.filter_by(
                event_id=e.id, status='present').count()
            rate = round((attended / registered * 100),
                         1) if registered > 0 else 0
            results.append({'event': e, 'registered': registered,
                           'attended': attended, 'rate': rate})
        return results

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

        # Need at least a handful of past events to fit a meaningful line (Ang Problem natin***)
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
