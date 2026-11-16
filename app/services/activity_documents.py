"""Activity document forms share existing storage, draft and recipient policies."""
from urllib.parse import urlsplit, parse_qs
from flask import abort, current_app, g, request, render_template, url_for, flash, redirect
from flask_login import current_user
from werkzeug.exceptions import HTTPException
from app.models import db
from app.models.workspace import FormDraft

FORM_ENDPOINTS = {'upload':'workspace.document_upload', 'announcement':'workspace.announcement_new'}
ANNOUNCEMENT_LABELS = {'event_update':'Event Update','last_call':'Last Call','cancelled_postponed':'Schedule Notice'}


def draft_identity(key):
    if not key.startswith('form:/') or key.startswith('form://') or len(key)>160 or '\\' in key or any(ord(c)<32 for c in key):
        return None
    try:
        target, values = current_app.url_map.bind('').match(urlsplit(key[5:]).path, method='GET')
    except HTTPException:
        return None
    if target == 'workspace.activity_documents':
        return values['event_id'], None
    for kind, endpoint in FORM_ENDPOINTS.items():
        if target == endpoint:
            return values['event_id'],kind
    return None


def document_url(event_id, view=None, page=None, endpoint='workspace.activity_documents', resume=None, anchor=None):
    view = view or request.args.get('view','documents')
    values = dict(event_id=event_id,view='announcements' if view=='announcements' else 'documents',
                  page=page if page is not None else max(1,request.args.get('page',1,type=int) or 1))
    previous = request.args.get('return_to','')
    if previous.startswith('/') and not previous.startswith('//') and '\\' not in previous and len(previous)<8192 and not any(ord(c)<32 for c in previous):
        try:
            parsed=urlsplit(previous)
            target, args=current_app.url_map.bind('').match(parsed.path,method='GET')
            selected=args.get('event_id') or parse_qs(parsed.query).get('event_id',[str(event_id)])[0]
            if target in ('workspace.activities','workspace.activity','workspace.activity_documents','workspace.report_results','workspace.reports') and str(selected)==str(event_id):
                values['return_to']=previous
        except HTTPException:
            pass
    if resume:values['resume']=resume
    return url_for(endpoint,**values,_anchor=anchor)


def form_context(event,kind):
    from app.routes.workspace import draft_for
    key=request.form.get('_draft_key') if request.method=='POST' else request.args.get('resume')
    key=key or 'form:'+url_for(FORM_ENDPOINTS[kind],event_id=event.id)
    identity=draft_identity(key)
    if identity is None or identity[0]!=event.id or identity[1] not in (None,kind):
        abort(400)
    draft=draft_for(key)
    if request.args.get('resume') and not draft and request.method=='GET':abort(404)
    payload=draft.payload if draft else {}
    values={name:(payload.get(name) or [''])[0] for name in ('message','announcement_type')}
    if request.method=='POST':values={name:request.form.get(name,'') for name in values}
    return dict(event=event,kind=kind,draft_key=key,legacy_draft=identity[1] is None,values=values,
                saved_upload=payload.get('_files',{}).get('file') if kind=='upload' else None,
                announcement_labels=ANNOUNCEMENT_LABELS,max_bytes=current_app.config['MILESTONE_MAX_BYTES'],
                document_url=document_url)


def form_failure(event,kind,errors,status=400):
    if request.endpoint in FORM_ENDPOINTS.values() or status>=500:
        return render_template('workspace/document_form.html',**form_context(event,kind),errors=errors),status
    for message in errors.values():flash(message,'error')
    return redirect(document_url(event.id,view='announcements' if kind=='announcement' else 'documents'))


def consume_draft(event,kind):
    """Consume only the submitted half of a legacy combined-page draft."""
    from app.routes.workspace import draft_for
    g.activity_document_draft_handled=True
    key=request.form.get('_draft_key','')
    if not key:return {}
    identity=draft_identity(key)
    if identity is None or identity[0]!=event.id or identity[1] not in (None,kind):abort(400)
    draft=draft_for(key)
    if not draft:return {}
    remaining=dict(draft.payload); consumed={}
    if kind=='upload':
        files=dict(remaining.get('_files',{}))
        if 'file' in files:consumed['file']=files.pop('file')
        if files:remaining['_files']=files
        else:remaining.pop('_files',None)
        remaining.pop('category',None)
    else:
        remaining.pop('message',None);remaining.pop('announcement_type',None)
    if remaining:draft.payload=remaining
    else:db.session.delete(draft)
    return consumed


def legacy_resumes(event):
    resumes=[]
    rows=FormDraft.query.filter_by(user_id=current_user.id,campus_id=current_user.campus_id).all()
    requested=request.args.get('resume')
    for draft in rows:
        if draft_identity(draft.key)!=(event.id,None) or (requested and requested!=draft.key):continue
        for kind,available in [('upload',draft.payload.get('_files',{}).get('file')),('announcement',draft.payload.get('message') or draft.payload.get('announcement_type'))]:
            if available:
                resumes.append(dict(label='Resume Saved Upload' if kind=='upload' else 'Resume Saved Announcement',
                    url=document_url(event.id,view='documents' if kind=='upload' else 'announcements',endpoint=FORM_ENDPOINTS[kind],resume=draft.key)))
    if requested and not resumes:abort(404)
    return resumes
