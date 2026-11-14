"""Authorized workspace report rows shared by screens, charts, and exports."""
from calendar import monthrange
from datetime import date, datetime, time, timedelta

from flask import abort
from sqlalchemy import case, func, or_
from sqlalchemy.orm import joinedload

from app.models import db
from app.models.event import Event, Registration, Attendance, Campus, SdgGoal
from app.models.user import User


def reporting_period(args, now):
    year = args.get('year', type=int) if 'year' in args else args.get('goal_year', now.year, type=int)
    if year is None or not 1900 <= year <= 9998:
        abort(400, description='Choose a reporting year from 1900 to 9998.')
    period = args.get('period', 'annual')
    segment = args.get('segment', 1, type=int)
    if period in ('this_month', 'last_month'):
        start = now.date().replace(day=1)
        if period == 'last_month':
            end = start - timedelta(days=1)
            start = end.replace(day=1)
        else:
            end = now.date()
        period = 'custom'
    elif period == 'all':
        start = end = None
    elif period == 'custom' or ('period' not in args and (args.get('start_date') or args.get('end_date'))):
        try:
            start = date.fromisoformat(args.get('start_date', ''))
            end = date.fromisoformat(args.get('end_date', ''))
            if start > end or start.year < 1900 or end.year > 9998:
                raise ValueError
        except ValueError:
            abort(400, description='Choose valid start and end dates, with the end on or after the start.')
        period = 'custom'
    else:
        maximum = {'annual':1, 'semiannual':2, 'quarterly':4}.get(period)
        if not maximum or segment is None or not 1 <= segment <= maximum:
            abort(400, description='Choose a valid reporting period and period number.')
        months = 12 // maximum
        first = 1 + (segment - 1) * months
        last = first + months - 1
        start, end = date(year, first, 1), date(year, last, monthrange(year, last)[1])
    previous = None
    if start:
        if period == 'custom':
            try:
                previous = (start - (end - start + timedelta(days=1)), start - timedelta(days=1))
            except OverflowError:
                previous = None
        else:
            previous_end = start - timedelta(days=1)
            months = 12 if period == 'annual' else 6 if period == 'semiannual' else 3
            index = previous_end.year * 12 + previous_end.month - months
            previous = (date(index // 12, index % 12 + 1, 1), previous_end)
    return dict(year=year, period=period, segment=segment or 1, start=start, end=end,
                previous=previous, period_label=f'{start:%d %b %Y} – {end:%d %b %Y}' if start else 'All recorded activity dates')


def legacy_report_url(dashboard=False):
    from flask import request, url_for
    values = request.args.to_dict(flat=False)
    view = values.pop('view', [''])[0]
    historical = view == 'historical'
    if historical:
        return url_for('workspace.historical', **values)
    if view in ('summary', 'activities', 'participation'):
        values['view'] = [view]
    if 'department' in values and 'affiliation' not in values:
        values['affiliation'] = values.pop('department')
    if values.get('start_date', [''])[0] and values.get('end_date', [''])[0]:
        values['period'] = 'custom'
    if 'goal_year' in values and 'year' not in values:
        values['year'] = values.pop('goal_year')
    return url_for('workspace.overview' if dashboard else 'workspace.report_results', **values)


def _activity_rows(query, args, now):
    """Aggregate registrations once per activity, avoiding roster multiplication."""
    if args.get('sex','') not in ('','male','female','prefer_not_to_say','unrecorded'):
        abort(400,description='Choose a listed recorded-sex filter.')
    events = query.options(joinedload(Event.campus)).order_by(Event.date, Event.id).all()
    if not events:
        return []
    event_ids = query.with_entities(Event.id).statement
    eligible = Registration.status != 'cancelled'
    selected = db.true()
    sex, affiliation = args.get('sex', ''), args.get('affiliation', args.get('college_affiliation', ''))
    if sex:
        if sex not in ('male', 'female', 'prefer_not_to_say', 'unrecorded'):
            abort(400, description='Choose a listed recorded-sex filter.')
        selected &= (User.id.isnot(None) & User.sex.is_(None)) if sex == 'unrecorded' else User.sex == sex
    if affiliation:
        selected &= User.college_affiliation == affiliation
    valid = eligible & selected
    present = Attendance.status == 'present'
    def count(condition):
        return func.count(case((condition, 1)))
    facts = db.session.query(Registration.event_id,
        count(valid).label('registrations'),
        count(valid & Registration.user_id.isnot(None)).label('internal'),
        count(valid & Registration.external_participant_id.isnot(None)).label('external'),
        count(valid & present).label('present'),
        count(valid & present & Registration.status.in_(('confirmed', 'completed'))).label('verified'),
        count(eligible & Attendance.id.is_(None)).label('missing'),
    ).outerjoin(User, User.id == Registration.user_id).outerjoin(
        Attendance, Attendance.registration_id == Registration.id).filter(
        Registration.event_id.in_(event_ids)).group_by(Registration.event_id).all()
    by_id = {row.event_id:row._asdict() for row in facts}
    rows = []
    for event in events:
        metrics = by_id.get(event.id, dict(registrations=0, internal=0, external=0, present=0, verified=0, missing=0)).copy()
        conducted = event.lifecycle_status == 'approved' and event.end_date is not None and event.end_date <= now
        complete = conducted and metrics['missing'] == 0
        metrics.update(complete=complete, completed=metrics['present'] if conducted else 0,
            rate=round(metrics['present'] / metrics['registrations'] * 100, 1) if complete and metrics['registrations'] else None,
            target_met=(metrics['present'] >= event.target_participants) if complete and event.target_participants and not sex and not affiliation else None)
        attention = []
        if event.lifecycle_status == 'approved':
            if not event.end_date:
                attention.append('schedule_limit')
            elif conducted and metrics['missing']:
                attention.append('pending_attendance')
            elif event.date <= now < event.end_date and metrics['missing']:
                attention.append('record_attendance')
            if metrics['rate'] is not None and metrics['rate'] < 75:
                attention.append('low_attendance')
            if metrics['target_met'] is False:
                attention.append('missed_targets')
        wanted = args.get('attention', '')
        if wanted and wanted not in ('schedule_limit','pending_attendance','record_attendance','low_attendance','missed_targets'):
            abort(400, description='Choose a listed follow-up filter.')
        if wanted and wanted not in attention:
            continue
        rows.append(dict(event=event, conducted=conducted, attendees=metrics['verified'], metrics=metrics, attention=attention))
    return rows


def workspace_report(base, args, user, now, forced_campus=None):
    from app.annual_goals import summary, comparisons
    scope = reporting_period(args, now)
    campuses = Campus.query.order_by(Campus.name).all()
    campus_id = user.campus_id if user.role == 'coordinator' else forced_campus or args.get('campus_id', type=int)
    query = base
    if campus_id:
        query = query.filter(Event.campus_id == campus_id)
    selected = args.getlist('campus', type=int)
    raw = args.getlist('campus')
    mode = args.get('campus_mode', 'include')
    if mode not in ('include','exclude') or len(raw) != len(selected) or not set(selected) <= {c.id for c in campuses}:
        abort(400, description='Choose listed campuses and a valid selection mode.')
    if selected and user.role != 'coordinator':
        query = query.filter(or_(Event.campus_id.is_(None), Event.campus_id.notin_(selected)) if mode == 'exclude' else Event.campus_id.in_(selected))
    choices = query
    def in_period(query, start, end):
        if start:
            query = query.filter(Event.date >= datetime.combine(start,time.min),
                                 Event.date < datetime.combine(end + timedelta(days=1),time.min))
        return query
    department_choices = [r[0] for r in in_period(query,scope['start'],scope['end']).with_entities(Event.conducting_department).filter(
        Event.conducting_department.isnot(None),Event.conducting_department != '').distinct().order_by(Event.conducting_department)]
    department, event_id = args.get('department','').strip(), args.get('event_id',type=int)
    if department:
        query = query.filter(Event.conducting_department == department)
    if event_id:
        query = query.filter(Event.id == event_id)
    category, search = args.get('category',''), args.get('activity_name',args.get('q','')).strip()[:200]
    if category:
        query = query.filter(Event.category == category)
    if search:
        query = query.filter(Event.title.icontains(search,autoescape=True))
    if args.get('sdg_id'):
        sdg = args.get('sdg_id',type=int)
        if not sdg or not db.session.get(SdgGoal,sdg):
            abort(400, description='Choose a listed Sustainable Development Goal.')
        query = query.filter(Event.sdgs.any(SdgGoal.id == sdg))
    delivery = args.get('delivery','')
    if delivery in ('approved','conducted'):
        query = query.filter(Event.lifecycle_status == 'approved')
        if delivery == 'conducted':
            query = query.filter(Event.end_date.isnot(None),Event.end_date <= now)
    elif delivery:
        abort(400, description='Choose approved or conducted activities.')
    rows = _activity_rows(in_period(query,scope['start'],scope['end']),args,now)
    def totals(rows):
        return dict(approved=sum(r['event'].lifecycle_status == 'approved' for r in rows),
                    conducted=sum(r['conducted'] for r in rows), attendees=sum(r['attendees'] for r in rows if r['conducted']))
    current = totals(rows)
    deltas = {}
    if scope['previous']:
        previous = totals(_activity_rows(in_period(query,*scope['previous']),args,now))
        deltas = {key:current[key] - previous[key] for key in current}
    accounts = User.query.filter_by(role='volunteer')
    if campus_id:
        accounts = accounts.filter_by(campus_id=campus_id)
    elif selected:
        accounts = accounts.filter(User.campus_id.notin_(selected) | User.campus_id.is_(None) if mode == 'exclude' else User.campus_id.in_(selected))
    campus_chart = [dict(id=c.id,name=c.name,count=sum(r['conducted'] for r in rows if r['event'].campus_id == c.id))
                    for c in campuses if (not campus_id or c.id == campus_id) and (not selected or user.role == 'coordinator' or (c.id in selected) == (mode == 'include'))]
    bounds = (scope['start'],scope['end']) if scope['start'] else (min((r['event'].date.date() for r in rows),default=now.date()),max((r['event'].date.date() for r in rows),default=now.date()))
    first, last = (d.year * 12 + d.month - 1 for d in bounds)
    if last - first < 24:
        bins = [(i // 12,i % 12 + 1) for i in range(first,last+1)]
        month_labels = [date(y,m,1).strftime('%b %Y') for y,m in bins]
        monthly = [sum(r['conducted'] for r in rows if (r['event'].date.year,r['event'].date.month) == key) for key in bins]
    else:
        month_labels = [str(y) for y in range(bounds[0].year,bounds[1].year+1)]
        monthly = [sum(r['conducted'] for r in rows if r['event'].date.year == int(y)) for y in month_labels]
    users = User.query
    if campus_id:
        users = users.filter_by(campus_id=campus_id)
    categories = [r[0] for r in choices.with_entities(Event.category).filter(Event.category.isnot(None)).distinct().order_by(Event.category)]
    affiliations = [r[0] for r in users.with_entities(User.college_affiliation).filter(User.college_affiliation.isnot(None),User.college_affiliation != '').distinct().order_by(User.college_affiliation)]
    from app.dashboard import GUIDANCE_SCOPE_KEYS
    scope_query = {key:args.getlist(key) for key in GUIDANCE_SCOPE_KEYS if args.get(key)}
    scope_query.update(year=[str(scope['year'])],period=[scope['period']])
    if search:
        scope_query['activity_name']=[search]
    if scope['period'] == 'custom':
        scope_query.update(start_date=[str(scope['start'])],end_date=[str(scope['end'])])
    else:
        scope_query.pop('start_date',None); scope_query.pop('end_date',None)
    if campus_id:
        campus_label = next((c.name for c in campuses if c.id == campus_id),'Unavailable campus')
    elif selected:
        campus_label = ('Exclude ' if mode == 'exclude' else 'Include ') + ', '.join(c.name for c in campuses if c.id in selected)
    else:
        campus_label = 'All campuses'
    scope_parts = ['Campus scope: ' + campus_label]
    for key,label in [('department','Department'),('category','Category'),('activity_name','Activity search'),
                      ('sex','Recorded sex'),('affiliation','Participant affiliation'),('attention','Follow-up'),
                      ('delivery','Delivery'),('event_id','Activity ID'),('sdg_id','SDG ID')]:
        if args.get(key):
            scope_parts.append(label + ': ' + args.get(key).replace('_',' '))
    return dict(scope, **current, rows=rows, campus_id=campus_id, department=department,event_id=event_id,
        goals=summary(scope['year'],campus_id=campus_id),campus_goals=comparisons(scope['year']) if not campus_id else [],
        campuses=campuses,campus_chart=campus_chart,monthly=monthly,month_labels=month_labels,
        accounts=accounts.count(),now=now,deltas=deltas,department_choices=department_choices,
        activity_choices=choices.filter_by(lifecycle_status='approved').order_by(Event.title).all(),
        categories=categories,affiliations=affiliations,sdgs=SdgGoal.query.order_by(SdgGoal.number).all(),
        scope_query=scope_query,scope_label='; '.join(scope_parts),
        allow_scheduling=bool(scope['start'] and scope['start'] <= now.date() <= scope['end'] and delivery != 'conducted'
            and not any(args.get(key) for key in ('attention','event_id','activity_name','q','category','sdg_id','department','sex','affiliation'))),
        show_annual_findings=not any(args.get(key) for key in ('attention','event_id','activity_name','q','category','sdg_id','department')))


def follow_up_items(data):
    """Read-only findings; after-event corrections never reopen attendance."""
    labels = {
        'record_attendance':('Record Attendance Before the Event Ends','Record Attendance'),
        'pending_attendance':('Ended with Unrecorded Attendance','Open Correction Report'),
        'schedule_limit':('Attendance Is Read-Only: End Time Not Recorded','Review Schedule Limitation'),
        'missed_targets':('Verified Participation Did Not Reach the Numeric Target','Review Outreach and Target'),
        'low_attendance':('Attendance Is Below the Existing 75% Review Guide','Review Participation'),
    }
    from flask import url_for
    items = []
    for row in data['rows']:
        for code in row['attention']:
            title, action = labels[code]
            event = row['event']
            href = url_for('coordinator.attendance',event_id=event.id) if code == 'record_attendance' else url_for(
                'workspace.report_results',event_id=event.id,period='all',year=data['year'])
            items.append(dict(code=code,event=event,campus=event.campus,title=title,action=action,url=href,
                evidence=f"{row['metrics']['missing']} unrecorded; {row['metrics']['present']} recorded present / {row['metrics']['registrations']} registrations",
                scope=data['period_label']))
    from app.annual_goals import goal_guidance
    campuses = {campus.id:campus for campus in data['campuses']}
    allowed = {row['id'] for row in data['campus_chart']}
    goal_scopes = data['campus_goals'] if not data['campus_id'] else [dict(data['goals'],campus_id=data['campus_id'])]
    for goals in goal_scopes if data.get('show_annual_findings',True) else []:
        campus_id = goals['campus_id']
        if campus_id not in allowed:
            continue
        for tip in goal_guidance(goals):
            items.append(dict(code=tip['code'],event=None,campus=campuses.get(campus_id),
                title='No Approved Annual Targets' if tip['code'] == 'no_targets' else 'Annual Targets or Evidence Need Review',
                action='Review Annual Plans',url=url_for('goals.details',year=data['year'],campus=campus_id),
                evidence=tip['evidence'],scope=tip['scope_label']))
    if data.get('allow_scheduling'):
        for campus_id in allowed:
            if any(row['event'].campus_id == campus_id and row['event'].lifecycle_status == 'approved' for row in data['rows']):
                continue
            items.append(dict(code='no_activities',event=None,campus=campuses.get(campus_id),
                title='No Approved Activities Scheduled in This Period',action='Review Campus Schedule',
                url=url_for('director.activity_calendar',campus_id=campus_id) if data['campus_id'] is None else url_for('workspace.activities',campus_id=campus_id),
                evidence='No approved start-date records in the selected current period. Review planning before drawing conclusions.',scope=data['period_label']))
    coordinator_campuses = {row[0] for row in db.session.query(User.campus_id).filter(
        User.role == 'coordinator',User._is_active.is_(True)).distinct()}
    for item in items:
        item['has_coordinator'] = bool(item['campus'] and item['campus'].id in coordinator_campuses)
        item['scope_query'] = {key:values for key,values in data['scope_query'].items() if key not in ('campus','campus_mode','campus_id')}
        if item['campus']:
            item['scope_query']['campus_id']=[str(item['campus'].id)]
    order = ['record_attendance','pending_attendance','schedule_limit','no_targets','missed_targets','low_attendance','remaining_goals','no_activities']
    return sorted(items,key=lambda item:(order.index(item['code']),
                                         (item['event'].end_date if item['code'] == 'record_attendance' else item['event'].date) if item['event'] else datetime(data['year'],1,1),
                                         item['event'].id if item['event'] else item['campus'].id))
