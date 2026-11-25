"""Read-only reconciliation; review decisions are persisted only by explicit actions."""
import hashlib
import json
from datetime import datetime, time, timedelta
from flask import current_app, g, abort
from flask_login import current_user
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy import inspect, or_, and_
from werkzeug.datastructures import MultiDict
from app.models import db
from app.models.event import Event, Registration, Attendance
from app.models.finding_review import FindingReview, FindingReviewEvent
from app.services.staff_overview import FINDING_LABELS
from app.services.activity_workflow import local_now

GROUPS = {
    'attendance': ('Attendance Review', ('record_attendance','pending_attendance')),
    'annual': ('Annual Plans and Evidence', ('no_targets','remaining_goals')),
    'participation': ('Participation Outcomes', ('low_attendance','missed_targets')),
    'planning': ('Schedule and Planning', ('schedule_limit','no_activities')),
}
REASONS = {'historical_outcome_reviewed':'Historical Outcome Reviewed','evidence_completed':'Evidence Completed',
           'follow_up_no_longer_required':'Follow-up No Longer Required'}
RECOMMENDATIONS = {'':'No Recommendation','improve_outreach':'Improve Volunteer Outreach',
    'coordinate_departments':'Coordinate Earlier with Departments','review_scheduling':'Review Scheduling',
    'review_future_targets':'Review Future Targets','other':'Other — Explain in Assessment'}
ANNUAL = ('no_targets','remaining_goals')
FILTER_ONLY = ('sex','affiliation','college_affiliation','attention','finding_type','review_group','review_tab','view','page','tour','return_to','source','occurrence')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


def available():
    if not current_app.config.get('FINDING_REVIEWS_ENABLED'):return False
    if not hasattr(g,'finding_review_storage'):
        inspector=inspect(db.engine)
        g.finding_review_storage = all(inspector.has_table(model.__tablename__) and
            set(model.__table__.columns.keys()) <= {col['name'] for col in inspector.get_columns(model.__tablename__)}
            for model in (FindingReview,FindingReviewEvent))
        if g.finding_review_storage:
            g.finding_review_storage=any(c['column_names']==['finding_key'] for c in inspector.get_unique_constraints('finding_reviews'))
    return g.finding_review_storage


def serializer():
    return URLSafeSerializer(current_app.secret_key,salt='finding-review-source-v1')


def source_scope(args):
    from app.dashboard import GUIDANCE_SCOPE_KEYS
    return {key:args.getlist(key) for key in args if key in GUIDANCE_SCOPE_KEYS and key not in FILTER_ONLY}


def canonical(args):
    from app.routes.workspace import report_data
    return report_data(MultiDict((key,v) for key,values in source_scope(args).items() for v in values))


def generated(data):
    from app.services.workspace_reports import follow_up_items
    findings=follow_up_items(data)
    ids=[r['event'].id for r in data['rows']]
    evidence={}
    if ids:
        for reg_id,event_id,status,attendance_id,attendance_status in db.session.query(
            Registration.id,Registration.event_id,Registration.status,Attendance.id,Attendance.status
        ).outerjoin(Attendance,Attendance.registration_id==Registration.id).filter(Registration.event_id.in_(ids),
            Registration.status.in_(('confirmed','completed'))).order_by(Registration.id):
            evidence.setdefault(event_id,[]).append([reg_id,'eligible',attendance_id,attendance_status])
    data['_review_registration_evidence']=evidence
    rows={r['event'].id:r for r in data['rows']}
    data['_review_rows']=rows
    annual={p['campus_id']:p for p in data['campus_goals']} if not data['campus_id'] else {data['campus_id']:data['goals']}
    output=[]
    for finding in findings:
        event, campus, code = finding['event'],finding['campus'],finding['code']
        campus_id=campus.id if campus else None
        identity=dict(campus_id=campus_id,code=code)
        if event:identity['event_id']=event.id
        elif code in ANNUAL:identity['year']=data['year']
        else:identity['period']=[str(data['start']),str(data['end'])]
        if event:
            row=rows[event.id]
            facts=dict(event_id=event.id,campus_id=campus_id,lifecycle=event.lifecycle_status,
                start=event.date,end=event.end_date,target=event.target_participants,
                registrations=evidence.get(event.id,[]),metrics={k:v for k,v in row['metrics'].items() if k not in ('internal','external')})
            facts['metrics']['recorded_absent']=sum(r[3]=='absent' for r in evidence.get(event.id,[]))
        elif code in ANNUAL:
            facts=[{k:row.get(k) for k in ('target_id','target','actual','met','pending','deadline','overdue','comparison_rule','shared_key')}
                for row in annual[campus_id]['rows']]
        else:
            facts=[[r['event'].id,r['event'].date,r['event'].end_date,r['event'].lifecycle_status]
                   for r in data['rows'] if r['event'].campus_id==campus_id]
        snapshot=dict(title=finding['title'],code=code,campus_id=campus_id,campus=campus.name if campus else 'Unassigned',
            event_id=event.id if event else None,event_title=event.title if event else '',
            activity_date=event.date.isoformat() if event else None,year=event.date.year if event else data['year'],
            scope=finding['scope'],evidence=finding['evidence'],facts=json.loads(json.dumps(facts,default=str)))
        snapshot.update(period_start=str(data['start']) if data['start'] else None,period_end=str(data['end']) if data['end'] else None)
        annual_actionable=code in ANNUAL and (data['year']>=local_now().year or (code=='remaining_goals' and annual[campus_id]['pending']>0))
        output.append(dict(key=digest(identity),fingerprint=digest(facts),snapshot=snapshot,
            scope=finding['scope_query'],has_coordinator=finding['has_coordinator'],
            can_follow_up=(code in ('record_attendance','no_activities') or annual_actionable) and finding['has_coordinator']))
    return output


def group_for(code):
    return next(key for key,(_,codes) in GROUPS.items() if code in codes)


def scoped_query(data, history=False):
    ids=[row['id'] for row in data['campus_chart']]
    query=FindingReview.query.filter(FindingReview.campus_id.in_(ids))
    if current_user.role!='coordinator' and any(row['event'].campus_id is None for row in data['rows']):
        query=FindingReview.query.filter(or_(FindingReview.campus_id.in_(ids),FindingReview.campus_id.is_(None)))
    event_ids=[row['event'].id for row in data['rows']]
    annual=and_(FindingReview.finding_type.in_(ANNUAL),FindingReview.year==data['year']) if data.get('show_annual_findings',True) else db.false()
    planning=and_(FindingReview.finding_type=='no_activities',FindingReview.period_start==data['start'],FindingReview.period_end==data['end'])
    if history:
        planning=and_(FindingReview.finding_type=='no_activities',FindingReview.year==data['year']) if not data['start'] else and_(
            FindingReview.finding_type=='no_activities',FindingReview.period_start<=data['end'],FindingReview.period_end>=data['start'])
    same_source=db.session.query(Event.id).filter(Event.id==FindingReview.event_id,
        Event.campus_id.is_not_distinct_from(FindingReview.campus_id)).correlate(FindingReview).exists()
    missing=and_(~same_source,FindingReview.activity_date.isnot(None))
    if any(data['scope_query'].get(k) for k in ('event_id','activity_name','q','department','category','sdg_id','delivery')):missing=db.false()
    elif data['start']:
        missing=and_(missing,FindingReview.activity_date>=datetime.combine(data['start'],time.min),
            FindingReview.activity_date<datetime.combine(data['end']+timedelta(days=1),time.min))
    query=query.filter(or_(FindingReview.event_id.in_(event_ids),annual,planning,missing))
    return query


def inactive_evidence(saved,data):
    snapshot=dict(saved.snapshot)
    row=data['_review_rows'].get(snapshot.get('event_id'))
    if row and row['event'].campus_id!=saved.campus_id:row=None
    if snapshot['code'] in ANNUAL:
        plans=data['campus_goals'] if not data['campus_id'] else [dict(data['goals'],campus_id=data['campus_id'])]
        plan=next((p for p in plans if p['campus_id']==saved.campus_id),None)
        facts=[{k:r.get(k) for k in ('target_id','target','actual','met','pending','deadline','overdue','comparison_rule','shared_key')}
               for r in plan['rows']] if plan else []
    elif row:
        event=row['event'];metrics=dict(row['metrics'])
        registrations=data['_review_registration_evidence'].get(event.id,[])
        metrics['recorded_absent']=sum(r[3]=='absent' for r in registrations)
        facts=dict(event_id=event.id,start=event.date,end=event.end_date,lifecycle=event.lifecycle_status,
            target=event.target_participants,registrations=registrations,metrics=metrics)
        snapshot['evidence']=f"No longer detected: {metrics['present']} recorded present; {metrics['missing']} unrecorded; {metrics['defaulted']} system-default absences."
    elif snapshot['code']=='no_activities':
        facts=[[r['event'].id,r['event'].date,r['event'].end_date,r['event'].lifecycle_status]
            for r in data['rows'] if r['event'].campus_id==saved.campus_id]
    else:facts=dict(source_unavailable=True,event_id=snapshot.get('event_id'))
    snapshot['facts']=json.loads(json.dumps(facts,default=str))
    return dict(key=saved.finding_key,fingerprint=digest(facts),snapshot=snapshot,scope=saved.scope,can_follow_up=False)


def item_for(live, saved=None, current=None):
    changed=bool(live and saved and live['fingerprint']!=saved.fingerprint)
    item=dict(live or current) if live or current else dict(key=saved.finding_key,fingerprint=saved.fingerprint,snapshot=saved.snapshot,scope=saved.scope,can_follow_up=False)
    item.update(saved=saved,version=saved.version if saved else 0,
        status='needs_review' if changed or not saved else saved.status,
        changed=changed,detected=live is not None,
        assessment='' if changed or not saved else saved.assessment,
        recommendation='' if changed or not saved else saved.recommendation)
    item['token']=serializer().dumps(dict(key=item['key'],scope=item['scope']))
    item['revision']=digest([item['fingerprint'],live is not None,item['version'],item['status']])
    item['group']=group_for(item['snapshot']['code'])
    return item


def active_items(data):
    live={item['key']:item for item in generated(data)}
    saved={row.finding_key:row for row in scoped_query(data).all()}
    items=[]
    for key in dict.fromkeys([*live,*saved]):
        item=item_for(live.get(key),saved.get(key),inactive_evidence(saved[key],data) if key not in live else None)
        if item['status']!='closed':items.append(item)
    return items


def summary(data):
    items=active_items(data)
    return dict(total=len(items),follow_up_sent=sum(i['status']=='follow_up_sent' for i in items),
        groups=[dict(key=key,label=label,total=sum(i['group']==key for i in items)) for key,(label,_) in GROUPS.items()])


def authorized(row, completed=False):
    if current_user.role=='coordinator':
        if row.campus_id!=current_user.campus_id or not completed:abort(404)
    elif current_user.role not in ('director','admin'):abort(403)


def resolve(key, token='', completed=False):
    saved=FindingReview.query.filter_by(finding_key=key).first()
    if saved:authorized(saved, completed=completed)
    try:
        payload=serializer().loads(token) if token else dict(key=key,scope=saved.scope) if saved else None
    except BadSignature:abort(400,description='The review source is invalid. Return to Needs Attention.')
    if not payload or payload['key']!=key:abort(404)
    data=canonical(MultiDict((k,v) for k,vs in payload['scope'].items() for v in vs))
    live=next((item for item in generated(data) if item['key']==key),None)
    if not live and not saved:abort(409,description='This finding is no longer detected. Return to Needs Attention.')
    return item_for(live,saved,inactive_evidence(saved,data) if not live else None)


def history_query(data):
    return FindingReviewEvent.query.join(FindingReview,FindingReview.id==FindingReviewEvent.review_id).filter(
        FindingReview.id.in_(scoped_query(data,history=True).with_entities(FindingReview.id).statement),FindingReviewEvent.action=='closed')


def snapshot_content(review):
    return dict(snapshot=review.snapshot,fingerprint=review.fingerprint,assessment=review.assessment,
        recommendation=review.recommendation,closure_reason=review.closure_reason,status=review.status,version=review.version)


def mutate(item, action, form):
    """Caller commits review, notification, history and audit as one transaction."""
    from app.models.notification import Notification
    from app.models.user import User
    from app.utils.audit import log_activity
    if form.get('revision')!=item['revision'] or form.get('version',type=int)!=item['version']:
        abort(409,description='The evidence or review changed. Compare the latest values before saving.')
    if action not in ('save','close','reopen','follow_up','complete'):raise ValueError('Choose a listed review action.')
    note=form.get('assessment',item['assessment'] if action=='follow_up' else '').strip()
    recommendation=form.get('recommendation',item['recommendation'] if action=='follow_up' else '')
    reason=form.get('closure_reason','')
    if len(note)>4000 or recommendation not in RECOMMENDATIONS:raise ValueError('Keep the assessment within 4,000 characters and choose a listed recommendation.')
    if action in ('save','close','reopen','complete') and len(note)<10:raise ValueError('Enter an assessment of at least 10 characters.')
    if action=='close' and reason not in REASONS:raise ValueError('Choose a closure reason.')
    if action=='complete' and reason not in ('evidence_completed','follow_up_no_longer_required'):
        raise ValueError('Choose a listed completion reason.')
    if action=='reopen' and item['status']!='closed':raise ValueError('Only a closed review can be reopened.')
    if item['status']=='closed' and action!='reopen':raise ValueError('Reopen this review before changing its assessment.')
    if action=='follow_up' and not item.get('can_follow_up'):raise ValueError('This finding requires assessment rather than a corrective follow-up.')
    if action=='follow_up' and item['snapshot']['code']=='record_attendance':
        from app.services.activity_workflow import attendance_open
        event=Event.query.filter_by(id=item['snapshot']['event_id'],campus_id=item['snapshot']['campus_id']).populate_existing().with_for_update().first()
        if not event or not attendance_open(event):raise ValueError('The activity is no longer open for attendance. No reminder was sent.')
    if action=='follow_up' and item['saved'] and item['status']=='follow_up_sent' and not item['changed']:
        identity=dict(review_key=item['key'],fingerprint=item['fingerprint'],campus_id=item['snapshot']['campus_id'])
        recipients=User.query.filter_by(role='coordinator',campus_id=item['snapshot']['campus_id'],_is_active=True).all()
        if recipients and all(any(_same_notification(n,identity) for n in Notification.query.filter_by(
            user_id=person.id,notification_type='campus_guidance',is_read=False).all()) for person in recipients):
            g.finding_reminder_reused=True
            return item['saved']
    now=datetime.utcnow()
    row=item['saved']
    values=dict(fingerprint=item['fingerprint'],snapshot=item['snapshot'],scope=item['scope'],
        actor_id=current_user.id,updated_at=now,assessment=note,recommendation=recommendation,
        closure_reason=reason if action in ('close','complete') else '',
        status='closed' if action in ('close','complete') else 'follow_up_sent' if action=='follow_up' else 'needs_review' if action=='reopen' else item['status'])
    if row:
        count=FindingReview.query.filter_by(id=row.id,version=item['version']).update(dict(values,version=item['version']+1),synchronize_session=False)
        if count!=1:abort(409,description='Another Director updated this review. Reload before saving.')
        db.session.expire(row);db.session.refresh(row)
    else:
        snap=item['snapshot']
        row=FindingReview(finding_key=item['key'],campus_id=snap['campus_id'],event_id=snap['event_id'],year=snap['year'],finding_type=snap['code'],
            activity_date=datetime.fromisoformat(snap['activity_date']) if snap['activity_date'] else None,
            period_start=datetime.fromisoformat(snap['period_start']).date() if snap.get('period_start') else None,
            period_end=datetime.fromisoformat(snap['period_end']).date() if snap.get('period_end') else None,**values)
        db.session.add(row);db.session.flush()
    if action=='follow_up':
        recipients=User.query.filter_by(role='coordinator',campus_id=row.campus_id,_is_active=True).order_by(User.id).with_for_update().all()
        if not recipients:raise ValueError('No active Coordinator is assigned. The follow-up was not sent.')
        identity=dict(review_key=row.finding_key,fingerprint=row.fingerprint,campus_id=row.campus_id)
        for person in recipients:
            pending=Notification.query.filter_by(user_id=person.id,notification_type='campus_guidance',is_read=False).all()
            if any(_same_notification(n,identity) for n in pending):continue
            db.session.add(Notification(user_id=person.id,title='Campus Review Follow-Up',related_event_id=row.event_id,
                notification_type='campus_guidance',message=json.dumps(dict(version=2,identity=identity,
                    text=row.snapshot['title']+'. '+row.snapshot['evidence']+' '+{'record_attendance':'Complete attendance while the activity remains open.','no_targets':'Submit or review the campus annual plan.','remaining_goals':'Review outstanding annual evidence and agreed next steps.','no_activities':'Review this period and propose eligible activities.'}[row.finding_type],finding_type=row.finding_type,event_id=row.event_id,year=row.year))))
    if item['changed']:
        db.session.add(FindingReviewEvent(review_id=row.id,campus_id=row.campus_id,actor_id=current_user.id,actor_name=current_user.name,
            action='evidence_changed',content=snapshot_content(row)))
    event=FindingReviewEvent(review_id=row.id,campus_id=row.campus_id,actor_id=current_user.id,actor_name=current_user.name,
        action={'save':'assessed','close':'closed','complete':'closed','reopen':'reopened','follow_up':'follow_up_sent'}[action],content=snapshot_content(row))
    db.session.add(event);log_activity('finding_review_'+('completed' if action=='complete' else event.action),row,dict(fingerprint=row.fingerprint,version=row.version))
    if action=='follow_up' and row.finding_type=='record_attendance':
        if not attendance_open(db.session.get(Event,row.event_id)):
            raise ValueError('The activity ended before the reminder was saved. No reminder was sent.')
    return row


def _same_notification(note, identity):
    try:return json.loads(note.message).get('identity')==identity
    except (ValueError,TypeError):return False
