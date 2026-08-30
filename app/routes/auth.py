"""
Authentication Routes for PSU Volunteer Hub
=============================================
Handles login, registration, and logout.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from app.models.user import User, Interest, Skill, SystemSetting
from app.models import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

VOLUNTEER_TYPES = {'student', 'faculty', 'staff'}


def _password_min_length():
    setting = SystemSetting.query.filter_by(key='default_password_length').first()
    try:
        return max(8, int(setting.value)) if setting else 8
    except (TypeError, ValueError):
        return 8


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

        # Institutional email matching is case-insensitive; PSU IDs are exact.
        user = User.query.filter(or_(
            db.func.lower(User.email) == identifier.lower(),
            User.id_number == identifier,
        )).first()

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
    """Onboarding step 1: pick interests; connected skills reveal inline."""
    if request.method == 'POST':
        # Capture both interests and the skills revealed for them, then go
        # straight to account creation (the skills step is now inline).
        session['selected_interests'] = request.form.getlist('interests')
        session['selected_skills'] = request.form.getlist('skills')
        return redirect(url_for('auth.register'))

    from config import Config
    interest_skill_map = getattr(Config, 'INTEREST_SKILL_MAP', {})
    configured_names = list(interest_skill_map)
    all_interests = Interest.query.filter(
        Interest.name.in_(configured_names)
    ).order_by(Interest.name).all()
    interests_data = []
    for interest in all_interests:
        skill_names = interest_skill_map.get(interest.name, [])
        connected = (
            Skill.query.filter(Skill.name.in_(skill_names)).all()
            if skill_names else []
        )
        interests_data.append({'interest': interest, 'skills': connected})

    return render_template('interests.html', interests_data=interests_data)


@auth_bp.route('/skills', methods=['GET', 'POST'])
def skills():
    """Compatibility endpoint for the former separate skills step."""
    return redirect(url_for('auth.interests'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration."""
    from app.models.event import Campus
    if current_user.is_authenticated:
        # Allow starting a new registration even when a session is active
        # (e.g. an admin/director testing the signup flow): sign out first
        # instead of bouncing the visitor to their own dashboard.
        logout_user()

    campuses = Campus.query.all()
    interests = Interest.query.all()
    skills = Skill.query.all()

    if request.method == 'POST':
        # 1. Grab inputs from Signup.html
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        full_name = f"{first_name} {last_name}".strip()

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        id_number = request.form.get('id_number', '').strip() or None
        volunteer_type = request.form.get('volunteer_type', '').strip().lower()
        college_affiliation = request.form.get(
            'college_affiliation', '').strip()
        campus_id = request.form.get('campus', type=int)
        password_min = _password_min_length()

        # Validation
        errors = []
        if not first_name or not last_name:
            errors.append('First and Last Name are required.')
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < password_min:
            errors.append(
                f'Password must be at least {password_min} characters.')

        if not id_number:
            errors.append('PSU ID Number is required for volunteers.')
        if volunteer_type not in VOLUNTEER_TYPES:
            errors.append('Select Student, Faculty, or Staff.')
        if not college_affiliation:
            errors.append('College affiliation is required.')

        # Check duplicate email
        if email and User.query.filter(
                db.func.lower(User.email) == email).first():
            errors.append('An account with this email already exists.')
        if id_number and User.query.filter_by(id_number=id_number).first():
            errors.append('An account with this PSU ID already exists.')

        # Resolve campus string to Campus Model DB record
        campus_obj = db.session.get(Campus, campus_id) if campus_id else None
        if campus_obj is None:
            errors.append('Select a valid PSU campus.')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('Signup.html', campuses=campuses,
                                    interests=interests, skills=skills,
                                    password_min=password_min)

        # Public registration always creates a volunteer. Privileged roles
        # can only be assigned through the protected Admin interface.
        assigned_role = 'volunteer'

        # 3. Create User record
        user = User(
            name=full_name,
            email=email,
            id_number=id_number,
            role=assigned_role,
            volunteer_type=volunteer_type,
            college_affiliation=college_affiliation,
            campus_id=campus_obj.id if campus_obj else None
        )
        user.set_password(password)
        db.session.add(user)

        # 4. Attach Interest records carried over from the onboarding wizard
        #    (steps 1 & 2 stored them in the session).
        selected_interest_ids = request.form.getlist('interests') or session.get(
            'selected_interests', [])
        if selected_interest_ids:
            interest_ids = [
                int(i_id) for i_id in selected_interest_ids if str(i_id).isdigit()]
            chosen_interests = Interest.query.filter(
                Interest.id.in_(interest_ids)).all()

            # Populates user_interests pivot table automatically
            user.interests.extend(chosen_interests)

        # 4b. Attach Skill records carried over from the onboarding wizard
        selected_skill_ids = request.form.getlist('skills') or session.get(
            'selected_skills', [])
        if selected_skill_ids:
            skill_ids = [
                int(s_id) for s_id in selected_skill_ids if str(s_id).isdigit()]
            chosen_skills = Skill.query.filter(
                Skill.id.in_(skill_ids)).all()
            user.skills.extend(chosen_skills)

        # 5. Commit to MySQL
        db.session.flush()

        # Create a VolunteerProfile for volunteers so the recommendation
        # engine can cold-start instead of showing nothing.
        if assigned_role == 'volunteer':
            from app.models.user import VolunteerProfile
            db.session.add(VolunteerProfile(user_id=user.id))

        db.session.commit()

        # Clear session keys after successful registration
        session.pop('selected_interests', None)
        session.pop('selected_skills', None)

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('Signup.html', campuses=campuses,
                           interests=interests, skills=skills,
                           password_min=_password_min_length())


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
