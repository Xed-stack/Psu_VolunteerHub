"""Shared validation for existing activity fields and partner planning estimates."""


def partner_count(value,total,agency_id):
    if value in (None,''):
        return None
    if not isinstance(value,str) or not value.isascii() or not value.isdigit() or len(value)>9:
        raise ValueError('Expected Partner Participants must be a whole number from 0 to 999,999,999.')
    number=int(value)
    if number and not agency_id:
        raise ValueError('Choose a primary partner or signed MOA before entering Expected Partner Participants.')
    if total is not None and number>total:
        raise ValueError('Expected Partner Participants cannot exceed the Total Participant Target.')
    return number


def additional_agency_error(record,campus_id):
    from app.models.workspace import PartnerAgency
    ids=record.get('additional_agency_ids',[])
    if ids and PartnerAgency.query.filter(PartnerAgency.campus_id==campus_id,PartnerAgency.id.in_(ids)).count()!=len(ids):
        return 'Choose additional partner agencies belonging to your campus.'
    return None


def primary_agency(event):
    from sqlalchemy import inspect
    from app.models import db
    from app.models.workspace import ActivityProposal,PartnerAgreement
    if inspect(db.engine).has_table('activity_proposals'):
        record=db.session.get(ActivityProposal,event.id)
        if record and record.agency_id:
            return record.agency_id
    agreement=db.session.get(PartnerAgreement,event.agreement_id) if event.agreement_id else None
    return agreement.agency_id if agreement else None


def department_error(value,choices,previous=None):
    if value and value not in choices and value!=previous:
        return 'Choose a Conducting Department from your campus list.'
    return None


def stage_errors(payload,step,record=None,*,posting=False):
    from werkzeug.datastructures import MultiDict
    from app.routes.coordinator import _parse_event_schedule,_activity_categories,_max_event_slots
    from app.routes.workspace import audience_departments
    from app.services.proposal_record import validate_record,validate_posting_record,GROUPS,PARTICIPATION
    form=MultiDict((key,item) for key,values in payload.items() if not key.startswith('_') for item in (values if isinstance(values,list) else [values]))
    errors={}
    if step==2:
        for key,text in [('title','Activity Title'),('description','Public Activity Description')]:
            if not form.get(key,'').strip():errors[key]='Complete '+text+'.'
        schedule,error=_parse_event_schedule(form)
        if error:errors['date']=error
        if not error and form.getlist('aop_goal_ids'):
            from flask_login import current_user
            from app.services.aop_goals import validate_links
            try:validate_links(form.getlist('aop_goal_ids'),current_user.campus_id,schedule[0],schedule[1])
            except ValueError as exc:errors['aop_goal_ids']=str(exc)
        if form.get('category') not in _activity_categories():errors['category']='Choose an available Category.'
        error=department_error(form.get('conducting_department',''),audience_departments())
        if error:errors['conducting_department']=error
        from app.models.event import SdgGoal
        from app.models.user import Skill
        if SdgGoal.query.count() and not form.getlist('sdg_ids'):errors['sdg_ids']='Select at least one Sustainable Development Goal.'
        if SdgGoal.query.filter(SdgGoal.id.in_(form.getlist('sdg_ids'))).count()!=len(set(form.getlist('sdg_ids'))):errors['sdg_ids']='Choose available Sustainable Development Goals.'
        if Skill.query.filter(Skill.is_active.is_(True),Skill.id.in_(form.getlist('required_skills'))).count()!=len(set(form.getlist('required_skills'))):errors['required_skills']='Choose available skills.'
        if len(form.get('title',''))>200:errors['title']='Keep Activity Title within 200 characters.'
    if step==3:
        slots=form.get('slots',type=int)
        if slots is None or not 1<=slots<=_max_event_slots():errors['slots']='Enter a valid number of Volunteer Registration Slots.'
        total=form.get('target_participants',type=int)
        if form.get('target_participants') and (total is None or total<1):errors['target_participants']='Total Participant Target must be positive when provided.'
        days=form.get('cancellation_days','2')
        if len(days)>3 or not days.isascii() or not days.isdigit() or not 0<=int(days)<=365:errors['cancellation_days']='Withdrawal must close from 0 to 365 whole days before the activity.'
        if not set(form.getlist('departments'))<=set(audience_departments()):errors['departments']='Choose audience departments from your campus list.'
        from flask_login import current_user
        from app.models.workspace import PartnerAgency,PartnerAgreement
        agency_id=record.get('agency_id') if record else None
        additional_error=additional_agency_error(record or {},current_user.campus_id)
        if additional_error:errors['additional_agency_ids']=additional_error
        agency=PartnerAgency.query.filter_by(id=agency_id,campus_id=current_user.campus_id).first() if agency_id else None
        agreement_value=form.get('agreement_id')
        agreement=PartnerAgreement.query.join(PartnerAgency).filter(PartnerAgreement.id==agreement_value,PartnerAgency.campus_id==current_user.campus_id).first() if agreement_value else None
        if record and record.get('partnership_status')!='none' and not agency:errors['agency_id']='Choose an agency belonging to your campus.'
        if agreement_value and (not agreement or (record and (not agency or agreement.agency_id!=agency.id))):errors['agency_id']='Choose a campus MOA belonging to the primary agency.'
        if posting and record and record.get('partnership_status')=='existing' and not agreement_value:
            errors['partnership_status']='Select a signed MOA covering the activity start date.'
        agency_id=agency.id if agency else agreement.agency_id if agreement and not record else None
        try:partner_count(form.get('expected_partner_participants'),total,agency_id)
        except ValueError as exc:errors['expected_partner_participants']=str(exc)
    if record is not None:
        if posting:
            if step==3:errors.update(validate_posting_record(record))
            return errors
        groups=GROUPS if step==2 else PARTICIPATION
        keys={key for _,_,fields in groups for key in fields}
        if step==3:keys.update(('partnership_status','agency_id','psu_roles','partner_roles','partnership_duration','partnership_reason'))
        errors.update({key:value for key,value in validate_record(record).items() if key in keys})
    return errors
