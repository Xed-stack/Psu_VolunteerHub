"""Director-managed skills, interest connections and activity categories."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.models import db
from app.models.user import Skill, Interest, user_skills
from app.models.event import ActivityCategory, Event, event_skills
from app.utils.decorators import roles_required
from app.utils.audit import log_activity

catalogue_bp = Blueprint('catalogue', __name__, url_prefix='/workspace/catalogue')


def context(tab=None):
    values = request.form if request.method == 'POST' else request.args
    return dict(tab=tab or ('categories' if values.get('tab') == 'categories' else 'skills'),
                status='archived' if values.get('status') == 'archived' else 'active',
                q=values.get('q','').strip()[:100], page=max(1,values.get('page',1,type=int) or 1))


def back(tab=None):
    return url_for('catalogue.index', **context(tab))


@catalogue_bp.route('')
@login_required
@roles_required('director', 'admin')
def index():
    state = context()
    model = Skill if state['tab'] == 'skills' else ActivityCategory
    query = model.query.filter_by(is_active=state['status']=='active')
    if state['q']:
        query = query.filter(func.lower(model.name).contains(state['q'].lower(),autoescape=True))
    if model is Skill:
        query = query.options(selectinload(Skill.interests))
    rows = query.order_by(func.lower(model.name),model.id).paginate(page=state['page'],per_page=25,error_out=False)
    if rows.pages and state['page']>rows.pages:
        state['page']=rows.pages
        return redirect(url_for('catalogue.index',**state))
    user_counts = dict(db.session.query(user_skills.c.skill_id,func.count()).group_by(user_skills.c.skill_id).all()) if model is Skill else {}
    activity_counts = dict(db.session.query(event_skills.c.skill_id,func.count()).group_by(event_skills.c.skill_id).all()) if model is Skill else dict(db.session.query(Event.category,func.count()).group_by(Event.category).all())
    return render_template('workspace/catalogue.html',rows=rows,state=state,user_counts=user_counts,activity_counts=activity_counts)


@catalogue_bp.route('/skills/new',methods=['GET','POST'])
@catalogue_bp.route('/skills/<int:skill_id>/interests',methods=['GET','POST'])
@login_required
@roles_required('director', 'admin')
def skill_form(skill_id=None):
    skill = db.session.get(Skill,skill_id) if skill_id else None
    if skill_id and not skill:
        abort(404)
    errors={}
    duplicate=None
    name=skill.name if skill else ' '.join(request.form.get('name','').split())
    selected=request.form.getlist('interest_ids') if request.method=='POST' else [str(row.id) for row in skill.interests] if skill else []
    if request.method=='POST':
        interests=Interest.query.filter(Interest.id.in_(selected)).all()
        if not name or len(name)>100:
            errors['name']='Enter a skill name of 100 characters or fewer.'
        if not interests or len(interests)!=len(set(selected)):
            errors['interest_ids']='Choose at least one available interest.'
        duplicate=Skill.query.filter(func.lower(Skill.name)==name.lower()).first() if name else None
        if not skill and duplicate:
            errors['name']='That skill already exists. Find it in Active or Archived skills; restore it if needed.'
        if not errors:
            record=skill or Skill(name=name)
            record.interests=interests
            try:
                db.session.add(record);db.session.flush()
                log_activity('skill_interests_updated' if skill else 'skill_created',record,{'interest_ids':[row.id for row in interests]})
                db.session.commit()
            except IntegrityError:
                db.session.rollback();errors['name']='That skill already exists. Refresh the catalogue and try again.'
            else:
                flash('Skill interests updated.' if skill else 'Skill added.','success')
                return redirect(back('skills'))
    return render_template('workspace/skill_form.html',skill=skill,name=name,selected=selected,interests=Interest.query.order_by(func.lower(Interest.name)).all(),errors=errors,duplicate=duplicate,state=context('skills'),return_url=back('skills'))


@catalogue_bp.route('/categories/new',methods=['POST'])
@login_required
@roles_required('director', 'admin')
def category_create():
    name=' '.join(request.form.get('name','').split())
    if not name or len(name)>50:
        flash('Enter a category name of 50 characters or fewer.','error')
    elif (duplicate:=ActivityCategory.query.filter(func.lower(ActivityCategory.name)==name.lower()).first()):
        if not duplicate.is_active:
            flash('That category is archived. Restore it below instead of adding it again.','warning')
            return redirect(url_for('catalogue.index',tab='categories',status='archived',q=duplicate.name))
        flash('That category already exists.','error')
    else:
        row=ActivityCategory(name=name)
        try:
            db.session.add(row);db.session.flush()
            log_activity('category_created',row,{'name':name})
            db.session.commit();flash('Activity category added.','success')
        except IntegrityError:
            db.session.rollback();flash('That category already exists. Refresh the catalogue and try again.','error')
    return redirect(back('categories'))


@catalogue_bp.route('/<kind>/<int:record_id>/<action>',methods=['POST'])
@login_required
@roles_required('director', 'admin')
def change_state(kind,record_id,action):
    if kind not in ('skills','categories') or action not in ('archive','restore'):
        abort(404)
    model=Skill if kind=='skills' else ActivityCategory
    row=db.session.get(model,record_id)
    if not row:
        abort(404)
    if model is ActivityCategory and row.name.casefold()=='general' and action=='archive':
        flash('General must remain available and cannot be archived.','error')
    elif row.is_active != (action=='restore'):
        row.is_active=action=='restore'
        log_activity('catalogue_'+action,row,{'name':row.name})
        db.session.commit();flash('Item restored.' if row.is_active else 'Item archived. Existing assignments have been preserved.','success')
    return redirect(back(kind))
