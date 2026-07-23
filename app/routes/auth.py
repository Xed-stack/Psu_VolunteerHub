"""
Authentication Routes for PSU Volunteer Hub
=============================================
Handles login, registration, and logout.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User, Interest
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


@auth_bp.route('/interests', methods=['GET', 'POST'])
def interests():
    if request.method == 'POST':
        selected_interests = request.form.getlist('interests')

        # Store in session to carry over to the signup step
        session['selected_interests'] = selected_interests

        # Redirect to signup page
        return redirect(url_for('auth.register'))

    all_interests = Interest.query.all()
    return render_template('interests.html', interests=all_interests)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration."""
    from app.models.event import Campus
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    campuses = Campus.query.all()

    if request.method == 'POST':
        # 1. Grab inputs from Signup.html
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        full_name = f"{first_name} {last_name}".strip()

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Maps to the account_type dropdown in Signup.html
        account_type = request.form.get('account_type', 'volunteer')
        id_number = request.form.get('id_number', '').strip()

        # Campus string key from dropdown (e.g., 'lingayen', 'urdaneta')
        campus_key = request.form.get('campus')

        # Validation
        errors = []
        if not first_name or not last_name:
            errors.append('First and Last Name are required.')
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters.')

        if account_type == 'volunteer' and not id_number:
            errors.append('PSU ID Number is required for volunteers.')

        # Check duplicate email
        if email and User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')

        # Resolve campus string to Campus Model DB record
        campus_obj = None
        if campus_key:
            campus_obj = Campus.query.filter(
                Campus.name.ilike(f"%{campus_key}%")).first()

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('Signup.html', campuses=campuses)

        # 2. Map role choices
        # Supported user roles: 'volunteer', 'coordinator', 'director', 'admin'
        role_mapping = {
            'volunteer': 'volunteer',
            'coordinator': 'coordinator',
            'executive': 'director'
        }
        assigned_role = role_mapping.get(account_type, 'volunteer')

        # 3. Create User record
        user = User(
            name=full_name,
            email=email,
            id_number=id_number,
            role=assigned_role,
            campus_id=campus_obj.id if campus_obj else None
        )
        user.set_password(password)

        # 4. Attach Interest records stored from step 1 (Interests page)
        selected_interest_ids = session.get('selected_interests', [])
        if selected_interest_ids:
            interest_ids = [
                int(i_id) for i_id in selected_interest_ids if str(i_id).isdigit()]
            chosen_interests = Interest.query.filter(
                Interest.id.in_(interest_ids)).all()

            # Populates user_interests pivot table automatically
            user.interests.extend(chosen_interests)

        # 5. Commit to MySQL
        db.session.add(user)
        db.session.commit()

        # Clear session key after successful registration
        session.pop('selected_interests', None)

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('Signup.html', campuses=campuses)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
