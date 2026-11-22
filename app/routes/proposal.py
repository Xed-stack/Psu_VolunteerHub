"""Staff proposal capture, review and activity-context agency selection."""
import json
from copy import deepcopy
from pathlib import Path
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import MultiDict
from app.models import db
from app.models.workspace import ActivityProposal, PartnerAgency, PartnerAgreement
from app.models.user import Skill
from app.models.event import SdgGoal
from app.services.activity_workflow import save_document, stage_cover
from app.services.proposal_record import (SCALARS, CHOICES, TABLES, GROUPS, PARTICIPATION,
    normalize_record, record_from_form, validate_posting_record, capture_proposal, budget_totals,
    POSTING_RECORD_KEYS, POSTING_CAPTURE_KEYS, POSTING_PROFILE)
from app.utils.decorators import role_required, roles_required

proposal_bp = Blueprint('proposal', __name__, url_prefix='/workspace')


def proposal_context():
    return dict(proposal_scalars=SCALARS, proposal_choices=CHOICES, proposal_tables=TABLES,
                proposal_groups=GROUPS, participation_groups=PARTICIPATION)


def stored_record(payload):
    values = payload.get('proposal_record',['{}'])
    return normalize_record(values[0] if isinstance(values,list) and values else '{}')


def _remove_proposal(document):
    if isinstance(document,dict) and document.get('path'):
        folder=Path(current_app.config['PRIVATE_UPLOAD_FOLDER'])/'proposals'
        try:
            (folder/Path(document['path']).name).unlink(missing_ok=True)
        except OSError:
            current_app.logger.warning('An unused private proposal file could not be removed.')


def _capture_file(file):
    document, _ = save_document(file)
    path=Path(current_app.config['PRIVATE_UPLOAD_FOLDER'])/'proposals'/document['path']
    record, operational, capture, readable = capture_proposal(path.read_bytes(),document['name'])
    document['readable']=readable
    return document, record, operational, capture


def create_proposal(step, draft):
    from app.routes.workspace import (ACTIVITY_FIELDS, publish_draft, notify_audience,
        remove_staged_files, audience_departments, partner_url)
    from app.routes.coordinator import _activity_categories, _max_event_slots
    from app.utils.audit import log_activity
    payload=deepcopy(draft.payload)
    record=stored_record(payload)
    errors, field_errors = [], {}
    if step>1 and not payload.get('_proposal'):
        return redirect(url_for('workspace.create_activity',step=1))
    if request.method=='POST':
        created_cover=None
        try:
            if step==1:
                if request.form.get('cancel_replacement') == 'yes':
                    previous=payload.pop('_proposal_replacement',{}).get('document')
                    draft.payload=payload
                    db.session.commit()
                    _remove_proposal(previous)
                    return redirect(url_for('workspace.create_activity',step=1))
                if request.form.get('apply_replacement') == 'yes':
                    pending=payload.get('_proposal_replacement')
                    if not pending:
                        raise ValueError('No replacement proposal is waiting for review.')
                    allowed=(set(pending['record']) & POSTING_RECORD_KEYS)|set(pending['operational'])
                    selected=set(request.form.getlist('replace_fields'))
                    if not selected<=allowed:
                        abort(400)
                    for key in selected:
                        if key in pending['record']:
                            record[key]=pending['record'][key]
                        if key in pending['operational']:
                            payload[key]=[pending['operational'][key]]
                    previous=payload.get('_proposal')
                    payload['_proposal']=pending['document']
                    payload['_capture']={key:(value if key in selected or not (record.get(key) or payload.get(key)) else dict(state='Needs Review',source='Retained from the previous proposal',excerpt='This value was kept. Check it against the replacement document.'))
                                         for key,value in pending['capture'].items()}
                    payload.pop('_proposal_replacement',None)
                    payload['proposal_record']=[json.dumps(record,ensure_ascii=False)]
                    draft.payload=payload
                    db.session.commit()
                    _remove_proposal(previous)
                    return redirect(url_for('workspace.create_activity',step=2))
                file=request.files.get('proposal')
                if file and file.filename:
                    document,captured,operational,capture=_capture_file(file)
                    if payload.get('_proposal'):
                        previous=payload.get('_proposal_replacement',{}).get('document')
                        payload['_proposal_replacement']=dict(document=document,record=captured,operational=operational,capture=capture)
                        draft.payload=payload
                        db.session.commit()
                        _remove_proposal(previous)
                        return redirect(url_for('workspace.create_activity',step=1))
                    payload['_proposal']=document
                    payload['_capture']=capture
                    for key,value in captured.items():
                        if not record.get(key):record[key]=value
                    for key,value in operational.items():
                        if not payload.get(key):payload[key]=[value]
                    payload['proposal_record']=[json.dumps(record,ensure_ascii=False)]
                    flash('Proposal attached. Review captured values and complete missing information.' if document['readable'] else
                          'Proposal attached. Text could not be captured; complete the fields manually.','info')
                elif not payload.get('_proposal') and not request.form.get('save_draft'):
                    raise ValueError('Choose the approved PDF or DOCX proposal.')
            else:
                remove=None
                row_action=request.form.get('row_action','')
                if row_action:
                    parts=row_action.split(':')
                    if len(parts)!=3 or parts[0] not in ('add','remove') or parts[1] not in TABLES or not parts[2].isdecimal():abort(400)
                    if parts[0]=='remove':remove=(parts[1],int(parts[2]))
                record=record_from_form(request.form,record,remove)
                payload['proposal_record']=[json.dumps(record,ensure_ascii=False)]
                for key in ACTIVITY_FIELDS-{'proposal_record'}:
                    if key in request.form:payload[key]=request.form.getlist(key)
                if step==2:
                    for key in ('required_skills','sdg_ids'):
                        payload[key]=request.form.getlist(key)
                    cover=request.files.get('cover_image')
                    if cover and cover.filename:
                        metadata=stage_cover(cover)
                        previous=payload.get('_files',{}).get('cover_image')
                        payload['_files']=dict(payload.get('_files',{}),cover_image=metadata)
                        if previous:remove_staged_files({'cover_image':previous})
                if step==3:
                    payload['departments']=request.form.getlist('departments')
                    document=request.files.get('partnership_document')
                    if document and document.filename:
                        saved,_=save_document(document)
                        previous=payload.get('_partnership_document')
                        payload['_partnership_document']=saved
                        # Keep the new file referenced before removing its predecessor.
                        draft.payload=payload
                        db.session.commit()
                        _remove_proposal(previous)
                    if record.get('partnership_status')=='none':
                        record['agency_id']=''
                        payload['agreement_id']=[]
                        payload['proposal_record']=[json.dumps(record,ensure_ascii=False)]
                if request.form.get('row_action'):
                    action,table,index=request.form['row_action'].split(':')
                    if table not in TABLES:abort(400)
                    # Empty rows are intentionally persisted only as form layout hints.
                    counts=dict(payload.get('_row_counts',{}))
                    rows=record.get(table,[])
                    if action=='remove':
                        # Submitted empty rows are removed by normalization already.
                        raw_count=len(request.form.getlist('pr.'+table+'.'+TABLES[table][1][0][0]))
                        record[table]=rows
                        counts[table]=max(1,raw_count-1)
                    elif action=='add':
                        counts[table]=min(50,max(len(rows),int(counts.get(table,1)))+1)
                    else:abort(400)
                    payload['_row_counts']=counts
                    payload['proposal_record']=[json.dumps(record,ensure_ascii=False)]
                    draft.payload=payload
                    db.session.commit()
                    return redirect(url_for('workspace.create_activity',step=step,_anchor='pr-'+table))
                target=request.form.get('save_step',type=int)
                if target and target not in (1,2,3,4):abort(400)
                if request.form.get('save_draft') or request.form.get('open_partners'):
                    target=step
                elif step in (2,3) and (target is None or target>step):
                    from app.services.activity_fields import stage_errors
                    field_errors.update(stage_errors(payload,step,record,posting=True))
                if step==4 and not target:
                    payload['_show_validation']=True
                    from app.services.activity_fields import stage_errors
                    field_errors=validate_posting_record(record)
                    for stage in (2,3):
                        field_errors.update(stage_errors(payload,stage,record,posting=True))
                    _,publication_errors=publish_draft(payload,validate_only=True)
                    errors.extend(publication_errors)
                    agency_id=record.get('agency_id','')
                    agency=PartnerAgency.query.filter_by(id=int(agency_id),campus_id=current_user.campus_id).first() if agency_id.isdecimal() else None
                    if record.get('partnership_status')!='none' and not agency:
                        field_errors['agency_id']='Choose an agency belonging to your campus.'
                    agreement_value=(payload.get('agreement_id') or [''])[0]
                    if agreement_value:
                        agreement=PartnerAgreement.query.filter_by(id=int(agreement_value)).first() if agreement_value.isdecimal() else None
                        if not agreement or not agency or agreement.agency_id!=agency.id:
                            field_errors['agency_id']='The selected MOA must belong to the selected agency.'
                    if record.get('partnership_status')=='existing' and not agreement_value:
                        field_errors['partnership_status']='Select a signed MOA covering the activity start date.'
                    unresolved={key for key,value in payload.get('_capture',{}).items() if key in POSTING_CAPTURE_KEYS and value['state']=='Needs Review'}
                    confirmed=set(request.form.getlist('capture_confirmed'))
                    if unresolved-confirmed:
                        errors.append('Confirm the captured posting details against the approved proposal.')
                    if request.form.get('proposal_reviewed')!='yes':
                        errors.append('Confirm that you reviewed the activity posting details.')
                    if not field_errors and not errors:
                        if not inspect(db.engine).has_table('activity_proposals'):
                            errors.append('Proposal storage is not configured. Ask the administrator to run the reviewed proposal migration; your draft is saved.')
                        else:
                            event,errors=publish_draft(payload)
                            if not errors:
                                created_cover=event.cover_image_path
                                db.session.add(event)
                                db.session.flush()
                                snapshot={label:payload.get(key,[]) for key,label in [('title','Activity Title'),('description','Public Activity Description'),
                                    ('date','Start (Philippine Time)'),('end_date','End (Philippine Time)'),('location','Location'),('category','Category'),
                                    ('slots','Volunteer Registration Slots'),('target_participants','Total Participant Target'),('expected_partner_participants','Expected Partner Participants'),
                                    ('conducting_department','Conducting Department'),('participant_type','Type of Participants'),
                                    ('cancellation_days','Withdrawal Closes: Days Before Start'),('departments','Audience Departments')]}
                                snapshot['Required Skills']=[skill.name for skill in event.required_skills_rel]
                                snapshot['Sustainable Development Goals']=['SDG '+str(goal.number)+' '+goal.name for goal in event.sdgs]
                                snapshot['Signed MOA']=[agreement.reference] if agreement_value and agreement else []
                                db.session.add(ActivityProposal(event_id=event.id,agency_id=agency.id if agency else None,
                                    content=dict(record,_form_profile=POSTING_PROFILE),capture=payload.get('_capture',{}),partnership_document=payload.get('_partnership_document'),
                                    publishing_snapshot=snapshot))
                                notify_audience(event)
                                log_activity('activity_created',event,{'proposal':True,'structured_proposal':1})
                                db.session.delete(draft)
                                db.session.commit()
                                remove_staged_files(payload.get('_files',{}))
                                _remove_proposal(payload.get('_proposal_replacement',{}).get('document'))
                                flash('Approved activity published.','success')
                                return redirect(url_for('workspace.activity',event_id=event.id))
            draft.payload=payload
            db.session.commit()
            if not errors and not field_errors:
                return redirect(partner_url('workspace.partners') if request.form.get('open_partners') else
                    url_for('workspace.create_activity',step=step if request.form.get('save_draft') else request.form.get('save_step',type=int) or min(step+1,4)))
        except ValueError as exc:
            errors.append(str(exc))
            draft.payload=payload
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            if created_cover:
                path=(Path(current_app.static_folder)/created_cover).resolve()
                if path.is_relative_to((Path(current_app.static_folder)/'uploads'/'events').resolve()):
                    path.unlink(missing_ok=True)
            db.session.refresh(draft)
            errors.append('The activity could not be saved. Your saved draft is retained. Try again.')
    record=stored_record(draft.payload)
    if draft.payload.get('_show_validation'):
        field_errors.update(validate_posting_record(record))
        _,validation_errors=publish_draft(draft.payload,validate_only=True)
        errors=list(dict.fromkeys(errors+validation_errors))
    data=MultiDict((key,value) for key,values in draft.payload.items() if not key.startswith('_') and key!='proposal_record'
                   for value in (values if isinstance(values,list) else [values]))
    if data.get('category') and data.get('category') not in _activity_categories():
        errors.append('The saved category is archived or unavailable. Choose an available category in Activity Details.')
    saved_skills=set(data.getlist('required_skills'))
    available_skills={str(row.id) for row in Skill.query.filter_by(is_active=True).all()}
    if saved_skills-available_skills:
        errors.append('A saved skill is archived or unavailable. Remove or replace the unavailable selection in Activity Details.')
    posting_capture={key:value for key,value in draft.payload.get('_capture',{}).items() if key in POSTING_CAPTURE_KEYS}
    return render_template('workspace/proposal_create.html',step=step,data=data,record=record,errors=errors,
        posting_capture=posting_capture,posting_record_keys=POSTING_RECORD_KEYS,
        field_errors=field_errors,payload=draft.payload,proposal=draft.payload.get('_proposal'),
        skills=Skill.query.filter_by(is_active=True).order_by(Skill.name).all(),sdgs=SdgGoal.query.order_by(SdgGoal.number).all(),
        categories=_activity_categories(),max_slots=_max_event_slots(),departments=audience_departments(),
        agencies=PartnerAgency.query.filter_by(campus_id=current_user.campus_id).order_by(PartnerAgency.name).all(),
        **proposal_context())


@proposal_bp.route('/partners/<int:agency_id>/use',methods=['POST'])
@login_required
@role_required('coordinator')
def use_agency(agency_id):
    from app.routes.workspace import partner_agency,draft_for
    if request.args.get('activity_context')!='create':abort(400)
    agency=partner_agency(agency_id)
    draft=draft_for('activity:new')
    if not draft or draft.payload.get('_full_proposal')!=1:abort(400)
    record=stored_record(draft.payload)
    record['agency_id']=str(agency.id)
    if record.get('partnership_status') not in ('existing','renewal','new'):record['partnership_status']='new'
    payload=dict(draft.payload,proposal_record=[json.dumps(record,ensure_ascii=False)])
    agreement_value=(payload.get('agreement_id') or [''])[0]
    if agreement_value:
        agreement=db.session.get(PartnerAgreement,int(agreement_value)) if agreement_value.isdecimal() else None
        if not agreement or agreement.agency_id!=agency.id:payload['agreement_id']=[]
    draft.payload=payload
    db.session.commit()
    return redirect(url_for('workspace.create_activity',step=3))


@proposal_bp.route('/activities/<int:event_id>/proposal-record')
@login_required
@roles_required('coordinator','director','admin')
def record(event_id):
    from app.routes.workspace import owned_event
    event=owned_event(event_id)
    proposal=db.session.get(ActivityProposal,event.id) if inspect(db.engine).has_table('activity_proposals') else None
    content=proposal.content if proposal else {}
    posting_record=content.get('_form_profile')==POSTING_PROFILE
    if posting_record:total=None
    else:_,total=budget_totals(content)
    return render_template('workspace/proposal_record.html',event=event,record=content,proposal_record=proposal,
                           posting_record=posting_record,budget_total=total,agency=db.session.get(PartnerAgency,proposal.agency_id) if proposal and proposal.agency_id else None,**proposal_context())


@proposal_bp.route('/activities/<int:event_id>/partnership-draft')
@login_required
@roles_required('coordinator','director','admin')
def partnership_document(event_id):
    from app.routes.workspace import owned_event,private_document
    event=owned_event(event_id)
    if not inspect(db.engine).has_table('activity_proposals'):abort(404)
    proposal=db.session.get(ActivityProposal,event.id)
    if not proposal or not proposal.partnership_document:abort(404)
    return private_document(proposal.partnership_document)
