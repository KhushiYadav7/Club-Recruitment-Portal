"""Email sending utilities - Using Mailjet API with beautiful professional templates

Mailjet Setup (NO DOMAIN NEEDED):
1. Sign up at https://mailjet.com (free: 200 emails/day, 6000/month)
2. Go to Account Settings → REST API → API Key Management
3. Copy API Key and Secret Key
4. Go to Account Settings → Sender addresses & domains
5. Add your email (just click verify link in inbox - NO DOMAIN!)
6. Set environment variables:
   - MAILJET_API_KEY=your-api-key
   - MAILJET_SECRET_KEY=your-secret-key
   - MAILJET_FROM_EMAIL=your-email@gmail.com (verified)
"""
from flask import current_app
import logging
import re
from mailjet_rest import Client

logger = logging.getLogger(__name__)


def strip_html_to_text(html):
    """Convert HTML to plain text for email"""
    # Remove style and script tags with content
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Replace br and p tags with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n ', '\n', text)
    return text.strip()


def is_email_configured():
    """Check if Mailjet is properly configured"""
    api_key = current_app.config.get('MAILJET_API_KEY')
    secret_key = current_app.config.get('MAILJET_SECRET_KEY')
    from_email = current_app.config.get('MAILJET_FROM_EMAIL')
    return bool(api_key and secret_key and from_email)


def send_email(to_email, subject, html_content):
    """Send email using Mailjet API
    
    Returns:
        bool: True always (never blocks workflow)
    """
    if not is_email_configured():
        logger.warning(f"Mailjet not configured. Skipping email to {to_email}")
        return True
    
    try:
        api_key = current_app.config['MAILJET_API_KEY']
        secret_key = current_app.config['MAILJET_SECRET_KEY']
        from_email = current_app.config['MAILJET_FROM_EMAIL']
        from_name = current_app.config.get('CLUB_NAME', 'Tech Club')
        
        mailjet = Client(auth=(api_key, secret_key), version='v3.1')
        
        # Generate plain text version (critical for avoiding spam filters)
        text_content = strip_html_to_text(html_content)
        
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": from_email,
                        "Name": from_name
                    },
                    "To": [
                        {
                            "Email": to_email
                        }
                    ],
                    "Subject": subject,
                    "TextPart": text_content,
                    "HTMLPart": html_content
                }
            ]
        }
        
        result = mailjet.send.create(data=data)
        
        if result.status_code == 200:
            logger.info(f"Email sent to {to_email}")
            return True
        else:
            logger.warning(f"Mailjet returned {result.status_code}: {result.json()}")
            return True  # Don't block workflow
        
    except Exception as e:
        logger.warning(f"Email failed to {to_email}: {str(e)}")
        return True  # Never block workflow


def send_credentials_email(user, temp_password):
    """Send login credentials with beautiful professional design"""
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    support_email = current_app.config.get('SUPPORT_EMAIL', 'support@techclub.com')
    login_url = f"{base_url}/auth/login"
    
    subject = f"Welcome to {club_name} Recruitment Portal"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f5f9;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 40px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">Welcome to {club_name}</h1>
                                <p style="color: #94a3b8; margin: 10px 0 0 0; font-size: 16px;">Recruitment Portal</p>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <p style="color: #334155; font-size: 16px; margin: 0 0 20px 0;">Hi <strong>{user.name}</strong>,</p>
                                
                                <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 30px 0;">
                                    Your account has been created for the {club_name} recruitment process. Use the following credentials to log in:
                                </p>
                                
                                <!-- Credentials Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); border-radius: 12px; border-left: 4px solid #14b8a6; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 24px;">
                                            <p style="margin: 0 0 12px 0; color: #0f766e; font-size: 14px;">
                                                <strong>Login URL:</strong><br>
                                                <a href="{login_url}" style="color: #0d9488; word-break: break-all;">{login_url}</a>
                                            </p>
                                            <p style="margin: 0 0 12px 0; color: #0f766e; font-size: 14px;">
                                                <strong>Username:</strong><br>
                                                <span style="color: #134e4a;">{user.email}</span>
                                            </p>
                                            <p style="margin: 0; color: #0f766e; font-size: 14px;">
                                                <strong>Temporary Password:</strong><br>
                                                <code style="background-color: #ffffff; padding: 4px 8px; border-radius: 4px; font-family: monospace; color: #0f172a; font-size: 16px;">{temp_password}</code>
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Warning -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef3c7; border-radius: 8px; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #92400e; font-size: 14px;">
                                                <strong>Important:</strong> You must change your password on first login for security reasons.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #475569; font-size: 15px; margin: 0 0 15px 0;">After logging in, you will be able to:</p>
                                <ul style="color: #64748b; font-size: 14px; line-height: 1.8; margin: 0 0 30px 0; padding-left: 20px;">
                                    <li>View available interview slots</li>
                                    <li>Book your preferred interview time</li>
                                    <li>View important announcements</li>
                                </ul>
                                
                                <!-- CTA Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center">
                                            <a href="{login_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%); color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">Login to Portal</a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                    Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488;">{support_email}</a>
                                </p>
                                <p style="margin: 0 0 8px 0; color: #94a3b8; font-size: 11px;">
                                    You received this email because you registered for {club_name} recruitment.
                                </p>
                                <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                                    {club_name}
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html)


def send_slot_confirmation_email(user, slot):
    """Send slot booking confirmation with professional design"""
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    support_email = current_app.config.get('SUPPORT_EMAIL', 'support@techclub.com')
    
    subject = f"Interview Slot Confirmed - {club_name}"
    
    # Format date properly
    from datetime import datetime
    slot_datetime = datetime.combine(slot.date, slot.start_time)
    slot_time = slot_datetime.strftime('%B %d, %Y at %I:%M %p')
    
    # Calculate duration if not a model property
    duration = None
    location = getattr(slot, 'location', None)
    
    if hasattr(slot, 'duration'):
        duration = slot.duration
    else:
        # Calculate duration from start_time and end_time
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), slot.start_time)
        end = datetime.combine(datetime.today(), slot.end_time)
        duration_delta = end - start
        duration = int(duration_delta.total_seconds() / 60)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f5f9;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #059669 0%, #047857 100%); padding: 40px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">Interview Confirmed</h1>
                                <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 16px;">Your slot has been booked</p>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <p style="color: #334155; font-size: 16px; margin: 0 0 20px 0;">Hi <strong>{user.name}</strong>,</p>
                                
                                <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 30px 0;">
                                    Your interview slot has been successfully confirmed!
                                </p>
                                
                                <!-- Interview Details Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-radius: 12px; border-left: 4px solid #10b981; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 24px;">
                                            <h3 style="margin: 0 0 15px 0; color: #065f46; font-size: 18px;">Interview Details</h3>
                                            <p style="margin: 0 0 12px 0; color: #047857; font-size: 14px;">
                                                <strong>Date & Time:</strong><br>
                                                <span style="color: #065f46; font-size: 16px;">{slot_time}</span>
                                            </p>
                                            <p style="margin: 0 0 12px 0; color: #047857; font-size: 14px;">
                                                <strong>Time:</strong><br>
                                                <span style="color: #065f46;">{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}</span>
                                            </p>
                                            {f'<p style="margin: 0 0 12px 0; color: #047857; font-size: 14px;"><strong>Duration:</strong><br><span style="color: #065f46;">{duration} minutes</span></p>' if duration else ''}
                                            {f'<p style="margin: 0; color: #047857; font-size: 14px;"><strong>Location:</strong><br><span style="color: #065f46;">{location}</span></p>' if location else ''}
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Tips Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #eff6ff; border-radius: 8px; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #1e40af; font-size: 14px;">
                                                <strong>Tip:</strong> Please arrive 5-10 minutes early. Good luck!
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #64748b; font-size: 14px; margin: 0;">
                                    We look forward to meeting you!
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                    Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488;">{support_email}</a>
                                </p>
                                <p style="margin: 0 0 8px 0; color: #94a3b8; font-size: 11px;">
                                    You received this email because you booked an interview slot with {club_name}.
                                </p>
                                <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                                    {club_name}
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html)


def send_password_reset_email(user, reset_token):
    """Send password reset link with professional design"""
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    support_email = current_app.config.get('SUPPORT_EMAIL', 'support@techclub.com')
    reset_url = f"{base_url}/auth/reset-password/{reset_token}"
    
    subject = f"Password Reset Request - {club_name}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f5f9;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #422a17 0%, #7c4a2d 100%); padding: 40px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">Password Reset</h1>
                                <p style="color: #facc15; margin: 10px 0 0 0; font-size: 16px;">{club_name}</p>
                            </td>
                        </tr>
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <p style="color: #334155; font-size: 16px; margin: 0 0 20px 0;">Hi <strong>{user.name}</strong>,</p>
                                
                                <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 30px 0;">
                                    We received a request to reset your password. Click the button below to create a new password:
                                </p>
                                
                                <!-- CTA Button -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 0 0 30px 0;">
                                    <tr>
                                        <td align="center">
                                            <a href="{reset_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">Reset Password</a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Info Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef3c7; border-radius: 8px; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #92400e; font-size: 14px;">
                                                This link will expire in 1 hour for security reasons.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #64748b; font-size: 14px; margin: 0 0 10px 0;">
                                    If you didn't request a password reset, please ignore this email or contact support if you have concerns.
                                </p>
                                
                                <p style="color: #94a3b8; font-size: 13px; margin: 0;">
                                    Or copy and paste this URL into your browser:<br>
                                    <a href="{reset_url}" style="color: #ea580c; word-break: break-all;">{reset_url}</a>
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #fdf8f6; padding: 24px 40px; text-align: center; border-top: 1px solid #eaddd7;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                    Need help? Contact us at <a href="mailto:{support_email}" style="color: #ea580c;">{support_email}</a>
                                </p>
                                <p style="margin: 0 0 8px 0; color: #94a3b8; font-size: 11px;">
                                    You received this email because you requested a password reset for your {club_name} account.
                                </p>
                                <p style="margin: 0; color: #7c4a2d; font-size: 12px;">
                                    {club_name}
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return send_email(user.email, subject, html)


def send_announcement_email(candidates, title, content):
    """Send announcement to multiple candidates with professional design"""
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    support_email = current_app.config.get('SUPPORT_EMAIL', 'support@techclub.com')
    
    # Simple subject without brackets - less likely to be flagged as spam
    subject = f"{title} - {club_name}"
    
    success = 0
    failed = 0
    
    for candidate in candidates:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f5f9;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 40px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">{title}</h1>
                                    <p style="color: #94a3b8; margin: 10px 0 0 0; font-size: 16px;">{club_name} Recruitment</p>
                                </td>
                            </tr>
                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px;">
                                    <p style="color: #334155; font-size: 16px; margin: 0 0 20px 0;">Hi <strong>{candidate.name}</strong>,</p>
                                    
                                    <!-- Announcement Box -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; border-radius: 12px; border-left: 4px solid #14b8a6; margin: 0 0 30px 0;">
                                        <tr>
                                            <td style="padding: 24px;">
                                                <div style="color: #334155; font-size: 15px; line-height: 1.6;">
                                                    {content}
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="color: #64748b; font-size: 14px; margin: 0;">
                                        Stay tuned for more updates!
                                    </p>
                                </td>
                            </tr>
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                    <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                        Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488;">{support_email}</a>
                                    </p>
                                    <p style="margin: 0 0 8px 0; color: #94a3b8; font-size: 11px;">
                                        You received this email because you are registered for {club_name} recruitment.
                                    </p>
                                    <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                                        {club_name}
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        if send_email(candidate.email, subject, html):
            success += 1
        else:
            failed += 1
    
    return success, failed
