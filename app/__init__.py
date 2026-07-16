"""
Flask Application Factory for PSU Volunteer Hub
=================================================
Creates and configures the Flask application instance.
"""
from flask import Flask
from flask_login import LoginManager
from app.models import db
from app.models.user import User, SystemSetting
from app.models.event import Event, Registration, Attendance, Milestone, Campus


def create_app(config_name='development'):
    """Create and return a configured Flask application instance."""
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static',
        static_url_path='/static'
    )

    # App configuration
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///psu_volunteer_hub.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Initialize extensions
    db.init_app(app)

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    from app.routes.volunteer import volunteer_bp
    app.register_blueprint(volunteer_bp)
    from app.routes.coordinator import coordinator_bp
    app.register_blueprint(coordinator_bp)
    from app.routes.director import director_bp
    app.register_blueprint(director_bp)
    from app.routes.admin import admin_bp
    app.register_blueprint(admin_bp)
    from app.routes.events import events_bp
    app.register_blueprint(events_bp)

    # Create tables and seed data on first run
    with app.app_context():
        db.create_all()
        _seed_campuses(app)
        _seed_events(app)
        _seed_users(app)

    # Register root routes
    @app.route('/')
    def home():
        from flask import render_template
        return render_template('Homepage.html')

    @app.route('/dashboard')
    def dashboard():
        """Central dashboard router based on user role."""
        from flask import render_template, redirect, url_for
        from flask_login import current_user

        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        role_routes = {
            'volunteer': 'events.volunteer_dash',
            'coordinator': 'coordinator.coordinator_dash',
            'director': 'director.director_dash',
            'admin': 'admin.admin_dash',
        }
        route = role_routes.get(current_user.role, 'volunteer_dash')
        return redirect(url_for(route))

    return app


def _seed_campuses(app):
    """Seed campus data on first run."""
    from app.models.event import Campus
    if Campus.query.count() == 0:
        campuses = [
            Campus(name='Lingayen', code='LINGAYEN'),
            Campus(name='Urdaneta', code='URDANETA'),
            Campus(name='Asingan', code='ASINGAN'),
            Campus(name='Bayambang', code='BAYAMBANG'),
            Campus(name='Binmaley', code='BINMALEY'),
            Campus(name='Infanta', code='INFANTA'),
            Campus(name='San Carlos', code='SANCARLOS'),
            Campus(name='Santa Maria', code='STAMARIA'),
            Campus(name='Alaminos', code='ALAMINOS'),
        ]
        for campus in campuses:
            db.session.add(campus)
        db.session.commit()


def _seed_events(app):
    """Seed sample events for testing recommendations."""
    from app.models.event import Event
    if Event.query.count() == 0:
        from datetime import datetime, timedelta
        from app.models import db

        events = [
            Event(title='Youth Coding Mentor',
                  description='Help Grade 6 students at San Carlos Central School learn basic Python and logic.',
                  date=datetime.now() + timedelta(days=7),
                  category='Technology',
                  required_skills='Teaching, Python, Communication, Public Speaking',
                  slots=20, campus_id=1),
            Event(title='Green Campus Initiative',
                  description='Participate in our monthly tree planting and sustainable landscaping project.',
                  date=datetime.now() + timedelta(days=14),
                  category='Environment',
                  required_skills='Environmental Conservation, Agriculture, Leadership',
                  slots=50, campus_id=1),
            Event(title='Community Food Drive',
                  description='Help organize and distribute relief packages to affected local barangays.',
                  date=datetime.now() + timedelta(days=10),
                  category='Community',
                  required_skills='Organizational, Communication, Physical Fitness',
                  slots=30, campus_id=2),
            Event(title='Rural Literacy Program',
                  description='Teach foundational reading and mathematics to children in remote communities.',
                  date=datetime.now() + timedelta(days=21),
                  category='Education',
                  required_skills='Teaching, Tutoring, Communication, Patience',
                  slots=15, campus_id=1),
            Event(title='Disaster Response Training',
                  description='Participate in basic first aid and disaster preparedness workshop.',
                  date=datetime.now() + timedelta(days=5),
                  category='Health',
                  required_skills='Medical, First Aid, Disaster Response, Teamwork',
                  slots=40, campus_id=3),
            Event(title='Community IT Support Workshop',
                  description='Help bridge the digital divide by teaching elderly residents how to use modern tools.',
                  date=datetime.now() + timedelta(days=30),
                  category='Technology',
                  required_skills='IT, Computer Skills, Teaching, Patience, Communication',
                  slots=25, campus_id=4),
            Event(title='Coastal Cleanup Drive',
                  description='Monthly environmental drive to preserve the Lingayen coastline.',
                  date=datetime.now() + timedelta(days=3),
                  category='Environment',
                  required_skills='Environmental Conservation, Teamwork, Physical Fitness',
                  slots=100, campus_id=1),
            Event(title='Community Wellness Fair',
                  description='Assist medical personnel in organizing a free health mission.',
                  date=datetime.now() + timedelta(days=45),
                  category='Health',
                  required_skills='Medical, First Aid, Organizational, Communication',
                  slots=60, campus_id=7),
            Event(title='Sustainable Farming Demo',
                  description='Learn about organic cultivation and irrigation management.',
                  date=datetime.now() + timedelta(days=60),
                  category='Environment',
                  required_skills='Agriculture, Environmental Conservation, Teaching',
                  slots=30, campus_id=8),
        ]
        for event in events:
            db.session.add(event)
        db.session.commit()


def _seed_users(app):
    """Seed example users for all roles."""
    from app.models.user import User, VolunteerProfile
    from app.models import db
    if User.query.count() == 0:
        seed_users_data = [
            dict(name='Student Volunteer', email='student@psu.edu', role='volunteer', campus_id=1),
            dict(name='Faculty Volunteer', email='faculty@psu.edu', role='volunteer', campus_id=2),
            dict(name='Staff Volunteer', email='staff@psu.edu', role='volunteer', campus_id=3),
            dict(name='Coordinator User', email='coordinator@psu.edu', role='coordinator', campus_id=1),
            dict(name='Director User', email='director@psu.edu', role='director', campus_id=1),
            dict(name='Admin User', email='admin@psu.edu', role='admin', campus_id=1),
        ]
        for data in seed_users_data:
            u = User(name=data['name'], email=data['email'], role=data['role'], campus_id=data['campus_id'])
            u.set_password('password')
            db.session.add(u)
            db.session.flush()
            if u.role == 'volunteer':
                profile = VolunteerProfile(user_id=u.id, skills='Teaching, Communication, Python', interests='Education, Technology, Environment')
                db.session.add(profile)
        db.session.commit()
