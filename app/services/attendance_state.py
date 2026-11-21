"""Read-only attendance defaults; recorded evidence is never rewritten."""
from datetime import datetime, timezone, timedelta
from flask import current_app
from sqlalchemy import and_, or_
from app.services.activity_workflow import local_now


def activation_time():
    value=current_app.config.get('ATTENDANCE_DEFAULTS_EFFECTIVE_FROM')
    if not value:
        return None
    try:
        result=datetime.fromisoformat(value) if isinstance(value,str) else value
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None)
    except (TypeError,ValueError,AttributeError):
        raise ValueError('ATTENDANCE_DEFAULTS_EFFECTIVE_FROM must be an ISO timestamp with an explicit time zone.') from None


def default_applies(event, now=None):
    activation=activation_time()
    return bool(activation and event.lifecycle_status=='approved' and event.end_date
                and activation<event.end_date<=(now or local_now()))


def state(registration, now=None):
    attendance=registration.attendance_record
    if attendance:
        return dict(status=attendance.status,basis='recorded')
    if registration.status in ('confirmed','completed') and default_applies(registration.event,now):
        return dict(status='absent',basis='system_default')
    return dict(status=None,basis='unrecorded')


def label(registration, now=None):
    value=state(registration,now)
    text={'present':'Attending','absent':'Not Attended','excused':'Excused'}.get(value['status'],'Unrecorded')
    return text+(' (System Default)' if value['basis']=='system_default' else '')


def default_condition(now=None):
    from app.models.event import Event, Registration, Attendance
    from app.models import db
    activation=activation_time()
    if activation is None:
        return db.false()
    return and_(Event.lifecycle_status=='approved',Event.end_date>activation,Event.end_date<=(now or local_now()),
                Registration.status.in_(('confirmed','completed')),Attendance.id.is_(None))


def roster_filter(query,status,event,now=None):
    from app.models.event import Registration,Attendance
    missing=~Registration.attendance_record.has()
    defaulted=and_(missing,Registration.status.in_(('confirmed','completed'))) if default_applies(event,now) else False
    if status=='unmarked':
        return query.filter(missing,~defaulted if defaulted is not False else True)
    if status=='absent':
        return query.filter(or_(Registration.attendance_record.has(Attendance.status=='absent'),defaulted))
    return query.filter(Registration.attendance_record.has(Attendance.status==status)) if status else query
