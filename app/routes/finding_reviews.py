"""Authorized review reads and explicit Director-only transactional decisions."""
from flask import Blueprint,abort,request,render_template,redirect,url_for,flash,g
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
from datetime import timedelta
from app.models import db
from app.models.finding_review import FindingReview,FindingReviewEvent
from app.models.event import Event
from app.services import finding_reviews as service
from app.utils.decorators import roles_required,role_required

finding_reviews_bp=Blueprint('finding_reviews',__name__,url_prefix='/workspace/finding-reviews')


@finding_reviews_bp.app_context_processor
def review_helpers():
    return dict(review_workflow_available=service.available)


@finding_reviews_bp.app_template_filter('review_pht')
def review_pht(value):
    return (value+timedelta(hours=8)).strftime('%d %b %Y, %I:%M %p Philippine time')


@finding_reviews_bp.app_template_filter('review_schedule')
def review_schedule(value):
    from datetime import datetime
    try:
        return datetime.fromisoformat(value) if isinstance(value,str) else value
    except ValueError:
        return None


def source_available(snapshot):
    event=db.session.get(Event,snapshot.get('event_id')) if snapshot.get('event_id') else None
    return bool(event and (current_user.role!='coordinator' or event.campus_id==current_user.campus_id))


def queue_view(args):
    data=service.canonical(args)
    tab=args.get('review_tab','reviewed' if current_user.role=='coordinator' else 'active')
    group=args.get('review_group','')
    code=args.get('finding_type','')
    if (tab not in ('active','reviewed') or group not in ('',*service.GROUPS) or code not in ('',*service.FINDING_LABELS)
            or len(args.getlist('review_group'))>1 or len(args.getlist('finding_type'))>1):abort(400)
    if current_user.role=='coordinator' and tab!='reviewed':abort(403)
    page=args.get('page',1,type=int)
    if page is None or page<1:abort(400)
    if tab=='active':
        items=service.active_items(data)
        if group:items=[i for i in items if i['group']==group]
        if code:items=[i for i in items if i['snapshot']['code']==code]
        total=len(items);pages=max(1,(total+24)//25);page=min(page,pages)
        items=items[(page-1)*25:page*25]
    else:
        query=service.history_query(data)
        if group:query=query.filter(FindingReview.finding_type.in_(service.GROUPS[group][1]))
        if code:query=query.filter(FindingReview.finding_type==code)
        total=query.count();pages=max(1,(total+24)//25);page=min(page,pages)
        items=query.order_by(FindingReviewEvent.created_at.desc(),FindingReviewEvent.id.desc()).offset((page-1)*25).limit(25).all()
    review_keys={row.id:row.finding_key for row in FindingReview.query.filter(FindingReview.id.in_([i.review_id for i in items])).all()} if tab=='reviewed' else {}
    return render_template('workspace/review_queue.html',**data,review_tab=tab,review_group=group,review_keys=review_keys,finding_labels=service.FINDING_LABELS,
        finding_type=code,groups=service.GROUPS,items=items,total=total,page=page,pages=pages,reasons=service.REASONS)


@finding_reviews_bp.route('/<string:key>',methods=['GET','POST'])
@login_required
@roles_required('director','admin','coordinator')
def detail(key):
    if not service.available():abort(503,description='Review management is unavailable. Return to Needs Attention.')
    occurrence=request.args.get('occurrence',type=int)
    if occurrence:
        event=db.session.get(FindingReviewEvent,occurrence)
        if not event or event.action!='closed':abort(404)
        row=db.session.get(FindingReview,event.review_id)
        if not row or row.finding_key!=key:abort(404)
        service.authorized(event,completed=True)
        if request.method=='POST':abort(403)
        return render_template('workspace/review_detail.html',item=None,occurrence=event,
            history=[],history_page=1,history_pages=1,reasons=service.REASONS,recommendations=service.RECOMMENDATIONS,error=None,submitted={},source_event_available=source_available(event.content['snapshot']))
    if current_user.role=='coordinator':abort(403)
    item=service.resolve(key,request.values.get('source',''))
    error=None;status=200
    submitted=request.form if request.method=='POST' else {}
    if request.method=='POST':
        if current_user.role!='director':abort(403)
        try:
            service.mutate(item,request.form.get('action',''),request.form)
            db.session.commit()
            action=request.form.get('action')
            message=('An equivalent unread reminder already exists.' if g.get('finding_reminder_reused') else 'Reminder sent to the campus Coordinator(s).') if action=='follow_up' else 'Review decision saved. Original evidence is unchanged.'
            flash(message,'info' if g.get('finding_reminder_reused') else 'success')
            from app.ui import follow_up_return
            destination=follow_up_return(request.form.get('queue_return')) if action=='follow_up' else None
            if destination:return redirect(destination)
            return redirect(url_for('finding_reviews.detail',key=key,source=item['token'],return_to=request.args.get('return_to') or None))
        except ValueError as exc:
            db.session.rollback();error=str(exc);status=400
        except IntegrityError:
            db.session.rollback();error='Another Director saved this review. Compare the latest evidence before saving.';status=409
        except SQLAlchemyError:
            db.session.rollback();error='The review could not be saved. Your entered assessment is retained; try again.';status=503
        except Exception as exc:
            if getattr(exc,'code',None)!=409:raise
            db.session.rollback();error=str(exc.description);status=409
    saved=item['saved']
    history_page=request.args.get('history_page',1,type=int)
    if history_page is None or history_page<1:abort(400)
    history_query=FindingReviewEvent.query.filter_by(review_id=saved.id) if saved else None
    history_pages=max(1,((history_query.count() if saved else 0)+24)//25)
    history_page=min(history_page,history_pages)
    history=history_query.order_by(FindingReviewEvent.id.desc()).offset((history_page-1)*25).limit(25).all() if saved else []
    return render_template('workspace/review_detail.html',item=item,occurrence=None,history=history,
        reasons=service.REASONS,recommendations=service.RECOMMENDATIONS,error=error,submitted=submitted,history_page=history_page,history_pages=history_pages,source_event_available=source_available(item['snapshot'])),status
