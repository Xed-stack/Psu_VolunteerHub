import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'}

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER', 'noreply@psu.edu.ph')

    CAMPUSES = ['Lingayen', 'Urdaneta', 'Asingan', 'Bayambang',
                'Binmaley', 'Infanta', 'San Carlos', 'Santa Maria', 'Sta. Maria']

    EVENT_CATEGORIES = [
        'Environment',
        'Education & Literacy',
        'Health & Wellness',
        'Community Development',
        'Disaster Response',
        'Technology & Digital',
        'Arts & Culture',
        'Sports & Recreation'
    ]

    SKILL_CATEGORIES = [
        'Teaching/Tutoring',
        'Medical/First Aid',
        'Engineering/Construction',
        'IT/Computer Skills',
        'Organizational/Management',
        'Communication/Public Speaking',
        'Creative Arts/Design',
        'Agriculture/Farming',
        'Environmental Conservation',
        'Disaster Response',
        'Counseling/Psychology',
        'Languages/Translation'
    ]

    # Maps each volunteer interest (EVENT_CATEGORIES) to the skills that are
    # most relevant, so the onboarding wizard can reveal connected skills
    # directly when an interest is selected.
    INTEREST_SKILL_MAP = {
        'Environment': ['Environmental Conservation', 'Agriculture/Farming'],
        'Education & Literacy': [
            'Teaching/Tutoring', 'Communication/Public Speaking',
            'Languages/Translation'
        ],
        'Health & Wellness': ['Medical/First Aid', 'Counseling/Psychology'],
        'Community Development': [
            'Organizational/Management', 'Communication/Public Speaking',
            'Creative Arts/Design'
        ],
        'Disaster Response': [
            'Disaster Response', 'Medical/First Aid', 'Engineering/Construction'
        ],
        'Technology & Digital': [
            'IT/Computer Skills', 'Engineering/Construction', 'Creative Arts/Design'
        ],
        'Arts & Culture': [
            'Creative Arts/Design', 'Communication/Public Speaking'
        ],
        'Sports & Recreation': [
            'Organizational/Management', 'Communication/Public Speaking'
        ],
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
                                             'mysql+pymysql://root:@localhost/psu_volunteer_hub')
    MAIL_SUPPRESS_SEND = True
    MAIL_DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # NOTE: Must never raise at import time — that would break test/CLI
    # collection whenever DATABASE_URL is unset. Enforcement happens in
    # create_app() when the production config is actually selected.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
