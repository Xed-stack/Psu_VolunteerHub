import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-fallback-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

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


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
                                             'mysql+pymysql://root:@localhost/psu_volunteer_hub')
    MAIL_SUPPRESS_SEND = True
    MAIL_DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError('DATABASE_URL must be set in production')


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
