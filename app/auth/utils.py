"""Authentication utilities"""
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models import User
from app.utils.email import send_credentials_email
from app.utils.security import hash_password, check_password, generate_random_password
import logging

logger = logging.getLogger(__name__)


def check_account_lockout(user):
    """Check if account is locked due to failed login attempts
    
    Args:
        user: User object
    
    Returns:
        bool: True if account is locked, False otherwise
    """
    if user.locked_until is None:
        return False
    
    # Check if lockout period has expired
    if datetime.utcnow() > user.locked_until:
        # Unlock account
        user.locked_until = None
        user.failed_login_attempts = 0
        db.session.commit()
        return False
    
    return True


def record_failed_login(user):
    """Increment failed login counter and lock account if needed
    
    Args:
        user: User object
    """
    user.failed_login_attempts += 1
    
    max_attempts = current_app.config['MAX_FAILED_ATTEMPTS']
    lockout_duration = current_app.config['LOCKOUT_DURATION']
    
    if user.failed_login_attempts >= max_attempts:
        # Lock account
        user.locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
        logger.warning(f"Account locked for user {user.email} due to failed login attempts")
    
    db.session.commit()


def reset_failed_attempts(user):
    """Clear failed login attempts on successful login
    
    Args:
        user: User object
    """
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()


def create_candidate(name, email, phone, department, year, skills='', send_email=True):
    """Create a new candidate user with temporary password
    
    Args:
        name (str): Candidate name
        email (str): Candidate email
        phone (str): Candidate phone number
        department (str): Department/Branch
        year (str): Academic year
        skills (str): Skills (optional)
        send_email (bool): Whether to send credentials email (default True)
    
    Returns:
        tuple: (User object, temporary_password) or (None, error_message)
    """
    from app.models import Application
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return None, f"User with email {email} already exists"
    
    try:
        # Generate temporary password
        temp_password = generate_random_password()
        
        # Create user
        user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=hash_password(temp_password),
            role='candidate',
            first_login=True,
            is_active=True
        )
        
        db.session.add(user)
        db.session.flush()  # Get user.id
        
        # Create application
        application = Application(
            user_id=user.id,
            department=department,
            year=year,
            skills=skills,
            status='pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Send credentials email if requested
        # Note: For bulk uploads, caller should pass send_email=False 
        # and send emails in batch after all users are created
        if send_email:
            send_credentials_email(user, temp_password)
        
        logger.info(f"Created candidate: {email}")
        return user, temp_password
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating candidate {email}: {str(e)}")
        return None, str(e)


def create_password_reset_token(user):
    """Create a password reset token for a user
    
    Args:
        user: User object
    
    Returns:
        str: The reset token
    """
    from datetime import timedelta
    from app.models import PasswordResetToken
    from app.utils.security import generate_token
    
    # Invalidate any existing unused tokens for this user
    PasswordResetToken.query.filter_by(
        user_id=user.id, 
        used=False
    ).update({'used': True})
    
    # Create new token
    token = generate_token(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    
    db.session.add(reset_token)
    db.session.commit()
    
    logger.info(f"Created password reset token for user {user.email}")
    return token
