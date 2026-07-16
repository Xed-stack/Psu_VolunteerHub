"""
Admin Routes for PSU Volunteer Hub
====================================
Manages user administration and system management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db
from app.models.user import User, SystemSetting
from app.models.event import Campus
from app.utils.decorators import role_required

admin_bp = Blueprint('admin', __name__, url_prefix='')


@admin_bp.route('/admin_dash')
@login_required
@role_required('admin')
def admin_dash():
    campus_id = request.args.get('campus_id', type=int)
    query = User.query
    if campus_id:
        query = query.filter(User.campus_id == campus_id)
    users = query.order_by(User.created_at.desc()).all()
    active_users = User.query.filter_by(_is_active=True).count()
    pending_approvals = User.query.filter_by(role='volunteer', _is_active=True).count()
    server_status = {'database': 'Connected', 'cache': 'Healthy', 'storage': 'OK', 'uptime': '99.9%'}
    audit_logs = []
    campuses = Campus.query.all()
    return render_template('Admin_mngmt_dash.html',
                           users=users,
                           server_status=server_status,
                           active_users=active_users,
                           pending_approvals=pending_approvals,
                           audit_logs=audit_logs,
                           selected_campus=campus_id,
                           campuses=campuses)


@admin_bp.route('/admin/users/deactivate/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.name} has been {status}.', 'success')
    return redirect(url_for('admin.admin_dash'))


@admin_bp.route('/admin/users/role/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '').strip()
    valid_roles = ['volunteer', 'coordinator', 'director', 'admin']
    if new_role not in valid_roles:
        flash('Invalid role specified.', 'error')
        return redirect(url_for('admin.admin_dash'))
    user.role = new_role
    db.session.commit()
    flash(f'User {user.name} role changed to {new_role}.', 'success')
    return redirect(url_for('admin.admin_dash'))


@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_user():
    campuses = Campus.query.all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'volunteer')
        campus_id = request.form.get('campus_id', type=int)
        errors = []
        if not name: errors.append('Name is required.')
        if not email: errors.append('Email is required.')
        if not password or len(password) < 6: errors.append('Password must be at least 6 characters.')
        if User.query.filter_by(email=email).first(): errors.append('Email already exists.')
        if errors:
            for e in errors: flash(e, 'error')
            return render_template('admin_user_form.html', user=None, campuses=campuses)
        user = User(name=name, email=email, role=role, campus_id=campus_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'User {name} created successfully.', 'success')
        return redirect(url_for('admin.admin_dash'))
    return render_template('admin_user_form.html', user=None, campuses=campuses)


@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    campuses = Campus.query.all()
    if request.method == 'POST':
        user.name = request.form.get('name', user.name).strip()
        user.email = request.form.get('email', user.email).strip()
        user.role = request.form.get('role', user.role)
        user.campus_id = request.form.get('campus_id', user.campus_id, type=int)
        db.session.commit()
        flash(f'User {user.name} updated.', 'success')
        return redirect(url_for('admin.admin_dash'))
    return render_template('admin_user_form.html', user=user, campuses=campuses)


@admin_bp.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '')
    if len(new_password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('admin.admin_dash'))
    user.set_password(new_password)
    db.session.commit()
    flash(f'Password reset for {user.name}.', 'success')
    return redirect(url_for('admin.admin_dash'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def settings():
    if request.method == 'POST':
        for key in request.form:
            setting = SystemSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = request.form[key]
            else:
                setting = SystemSetting(key=key, value=request.form[key])
                db.session.add(setting)
        db.session.commit()
        flash('Settings saved.', 'success')
    settings = {s.key: s.value for s in SystemSetting.query.all()}
    return render_template('settings.html', settings=settings)
