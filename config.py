import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Fix Render's postgres:// URL to postgresql:// for SQLAlchemy
    database_url = os.environ.get('DATABASE_URL') or 'sqlite:///recruitment.db'
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Connection pool settings for Neon serverless - optimized for free tier
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,     # Test connections before using
        'pool_recycle': 300,       # Recycle connections after 5 minutes
        'pool_size': 2,            # Reduced for free tier (less memory)
        'max_overflow': 3,         # Limited extra connections
        'pool_timeout': 30,        # Wait up to 30s for connection
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=int(os.environ.get('SESSION_TIMEOUT', 3600)))
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Mail Configuration (Legacy Flask-Mail - kept for compatibility)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    
    # Resend Email Configuration (Recommended - works on Render)
    # Get free API key at https://resend.com (3,000 emails/month free)
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
    RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
    
    # Application Configuration
    CLUB_NAME = os.environ.get('CLUB_NAME', 'Tech Club')
    SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@techclub.com')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    
    # Security Configuration
    MAX_FAILED_ATTEMPTS = int(os.environ.get('MAX_FAILED_ATTEMPTS', 5))
    LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION', 900))  # in seconds
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True
    
    # Override with environment variables in production
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
