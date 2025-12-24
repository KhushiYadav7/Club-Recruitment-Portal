"""Flask application factory and extensions initialization"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config
import logging
from logging.handlers import RotatingFileHandler
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login - use session.get for efficiency
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.candidate import candidate_bp
    from app.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(candidate_bp, url_prefix='/candidate')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register main routes
    from app import routes
    app.register_blueprint(routes.main_bp)
    
    # Error handlers
    register_error_handlers(app)
    
    # Logging configuration
    configure_logging(app)
    
    # Context processors
    @app.context_processor
    def inject_config():
        return {
            'CLUB_NAME': app.config['CLUB_NAME'],
            'SUPPORT_EMAIL': app.config['SUPPORT_EMAIL']
        }
    
    # Auto-create admin user from environment variables on startup
    create_admin_from_env(app)
    
    return app


def create_admin_from_env(app):
    """Create admin user from environment variables if not exists"""
    import bcrypt
    
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_name = os.environ.get('ADMIN_NAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if not all([admin_email, admin_name, admin_password]):
        return  # Skip if env vars not set
    
    with app.app_context():
        from app.models import User
        try:
            existing = User.query.filter_by(email=admin_email).first()
            if existing:
                return  # Admin already exists
            
            # Hash password with bcrypt
            password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            admin = User(
                name=admin_name,
                email=admin_email,
                password_hash=password_hash,
                role='admin',
                is_active=True,
                first_login=False
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info(f'Admin user created: {admin_email}')
        except Exception as e:
            app.logger.error(f'Failed to create admin: {str(e)}')
            db.session.rollback()


def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""
    from flask import render_template
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500


def configure_logging(app):
    """Configure application logging - stdout for cloud platforms"""
    if not app.debug and not app.testing:
        # Use stdout handler for cloud platforms (Render, Heroku, etc.)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
        ))
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Recruitment system startup')
