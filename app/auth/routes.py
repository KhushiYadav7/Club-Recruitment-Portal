"""Authentication routes"""
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app import db, limiter
from app.models import User
from app.utils.security import check_password, hash_password
from app.utils.validators import validate_password
from app.utils.audit import log_audit
from app.auth.utils import check_account_lockout, record_failed_login, reset_failed_attempts
import logging

logger = logging.getLogger(__name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Login route with account lockout protection"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('candidate.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Validate inputs
        if not email or not password:
            flash('Please provide both email and password', 'danger')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Invalid email or password', 'danger')
            logger.warning(f"Failed login attempt for non-existent user: {email}")
            return render_template('auth/login.html')
        
        # Check if user is active
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return render_template('auth/login.html')
        
        # Check account lockout
        if check_account_lockout(user):
            from datetime import datetime
            remaining_time = (user.locked_until - datetime.utcnow()).total_seconds()
            lockout_minutes = max(1, int(remaining_time // 60))
            flash(f'Account locked due to multiple failed attempts. Try again in {lockout_minutes} minutes.', 'danger')
            return render_template('auth/login.html')
        
        # Verify password
        if not check_password(user.password_hash, password):
            record_failed_login(user)
            remaining_attempts = 5 - user.failed_login_attempts
            if remaining_attempts > 0:
                flash(f'Invalid email or password. {remaining_attempts} attempts remaining.', 'danger')
            else:
                flash('Account locked due to multiple failed attempts.', 'danger')
            logger.warning(f"Failed login attempt for user: {email}")
            return render_template('auth/login.html')
        
        # Successful login
        reset_failed_attempts(user)
        login_user(user, remember=remember)
        
        # Log audit event
        log_audit(user.id, 'LOGIN', f'User logged in from {request.remote_addr}')
        logger.info(f"Successful login: {email}")
        
        # Check if first login
        if user.first_login:
            flash('Please change your password to continue', 'info')
            return redirect(url_for('auth.change_password'))
        
        # Redirect to appropriate dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('candidate.dashboard'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route"""
    log_audit(current_user.id, 'LOGOUT', 'User logged out')
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password route (forced on first login)"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password (skip for first login)
        if not current_user.first_login:
            if not check_password(current_user.password_hash, current_password):
                flash('Current password is incorrect', 'danger')
                return render_template('auth/change_password.html')
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return render_template('auth/change_password.html')
        
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.password_hash = hash_password(new_password)
        current_user.first_login = False
        db.session.commit()
        
        log_audit(current_user.id, 'PASSWORD_CHANGE', 'User changed password')
        flash('Password changed successfully', 'success')
        
        # Redirect to appropriate dashboard
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('candidate.dashboard'))
    
    return render_template('auth/change_password.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def forgot_password():
    """Forgot password route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        user = User.query.filter_by(email=email).first()
        
        # Always show success message to prevent email enumeration
        flash('If an account exists with this email, you will receive password reset instructions.', 'info')
        
        if user:
            from app.auth.utils import create_password_reset_token
            from app.utils.email import send_password_reset_email
            from flask import current_app
            
            # Generate reset token
            token = create_password_reset_token(user)
            
            # Generate reset URL
            reset_url = f"{current_app.config['BASE_URL']}/auth/reset-password/{token}"
            
            # Send reset email
            send_password_reset_email(user, reset_url)
            
            logger.info(f"Password reset requested for: {email}")
            log_audit(user.id, 'PASSWORD_RESET_REQUEST', 'User requested password reset')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    from app.models import PasswordResetToken
    from app.utils.security import hash_password
    
    # Find token
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid:
        flash('Invalid or expired reset link. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate passwords match
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Validate password strength
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Update password
        user = reset_token.user
        user.password_hash = hash_password(new_password)
        user.first_login = False
        
        # Mark token as used
        reset_token.used = True
        
        db.session.commit()
        
        log_audit(user.id, 'PASSWORD_RESET', 'User reset password via token')
        flash('Password reset successfully. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)
