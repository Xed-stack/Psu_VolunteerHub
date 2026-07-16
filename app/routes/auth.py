"""
Authentication Routes for PSU Volunteer Hub
=============================================
Handles login, registration, and logout.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login form submission and display login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not identifier or not password:
            flash('Please enter both email/ID and password.', 'warning')
            return render_template('login.html')

        # Lookup user by email (supports both email and ID number)
        user = User.query.filter_by(email=identifier).first()

        if user is None or not user.check_password(password):
            flash('Invalid email/ID or password.', 'error')
            return render_template('login.html')

        if not user.is_active:
            flash('Account is deactivated. Contact an administrator.', 'error')
            return render_template('login.html')

        login_user(user, remember=remember)

        # Redirect to role-appropriate dashboard
        role_redirects = {
            'volunteer': 'events.volunteer_dash',
            'coordinator': 'coordinator.coordinator_dash',
            'director': 'director.director_dash',
            'admin': 'admin.admin_dash',
        }
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for(role_redirects.get(user.role, 'dashboard')))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration."""
    from app.models.event import Campus
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    campuses = Campus.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        user_type = request.form.get('user_type', 'psu')
        id_number = request.form.get('id_number', '').strip()
        campus_id = request.form.get('campus_id', type=int)

        # Validation
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if user_type == 'psu' and not id_number:
            errors.append('ID Number is required for PSU students/faculty/staff.')
        if not campus_id:
            errors.append('Please select a campus.')

        # Check duplicate email
        if email and User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('login.html', campuses=campuses, user_type=user_type)

        # Create new user
        role = 'volunteer' if user_type == 'outsider' else 'volunteer'
        user = User(name=name, email=email, id_number=id_number, role=role, campus_id=campus_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('login.html', campuses=campuses)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
