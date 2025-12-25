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
from mailjet_rest import Client

logger = logging.getLogger(__name__)


def html_to_text(html):
    """Convert HTML email to plain text version
    
    This is critical for spam prevention - emails should always have both
    HTML and plain text versions.
    """
    import re
    
    # Remove HTML tags
    text = re.sub('<[^<]+?>', '', html)
    
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    
    return text


def is_email_configured():
    """Check if Mailjet is properly configured"""
    api_key = current_app.config.get('MAILJET_API_KEY')
    secret_key = current_app.config.get('MAILJET_SECRET_KEY')
    from_email = current_app.config.get('MAILJET_FROM_EMAIL')
    return bool(api_key and secret_key and from_email)


def send_email(to_email, subject, html_content, text_content=None):
    """Send email using Mailjet API with anti-spam best practices
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML version of email
        text_content: Plain text version (auto-generated if not provided)
    
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
        support_email = current_app.config.get('SUPPORT_EMAIL', 'support@techclub.com')
        
        # Generate plain text version if not provided (critical for spam prevention)
        if not text_content:
            text_content = html_to_text(html_content)
        
        mailjet = Client(auth=(api_key, secret_key), version='v3.1')
        
        # Enhanced email data with anti-spam headers
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
                    "TextPart": text_content,  # Plain text version (critical!)
                    "HTMLPart": html_content,
                    "CustomID": f"recruitment-{to_email}-{subject[:20]}",  # For tracking
                    # Anti-spam headers
                    "Headers": {
                        "Reply-To": support_email,  # Allows recipients to reply
                        "X-Mailer": f"{from_name} Recruitment System",
                        "X-Priority": "3",  # Normal priority (1-5, 3 is normal)
                        "Importance": "Normal",
                    },
                    # Email settings to improve deliverability
                    "TrackOpens": "enabled",  # Track opens for engagement metrics
                    "TrackClicks": "enabled"  # Track clicks for engagement metrics
                }
            ]
        }
        
        result = mailjet.send.create(data=data)
        
        # Log detailed response
        logger.info(f"Mailjet response for {to_email}: Status {result.status_code}, Body: {result.json()}")
        
        if result.status_code == 200:
            response_data = result.json()
            messages = response_data.get('Messages', [])
            if messages and messages[0].get('Status') == 'success':
                logger.info(f"✓ Email successfully sent to {to_email}")
                return True
            else:
                logger.error(f"✗ Mailjet accepted but may not deliver to {to_email}. Check sender verification!")
                logger.error(f"Response: {response_data}")
                return True  # Don't block workflow
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
                                                ⚠️ <strong>Important:</strong> You must change your password on first login for security reasons.
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
                                        <td align="center" style="padding-bottom: 20px;">
                                            <a href="{login_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%); color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">Login to Portal</a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #94a3b8; font-size: 13px; margin: 0; line-height: 1.5;">
                                    This is an automated message from {club_name} recruitment system. If you received this email by mistake, please ignore it or contact us.
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                    Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488; text-decoration: none;">{support_email}</a>
                                </p>
                                <p style="margin: 0 0 12px 0; color: #94a3b8; font-size: 12px;">
                                    © 2025 {club_name}. All rights reserved.
                                </p>
                                <p style="margin: 0; color: #cbd5e1; font-size: 11px;">
                                    You are receiving this email because you are registered for {club_name} recruitment.
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
    
    slot_time = slot.start_time.strftime('%B %d, %Y at %I:%M %p')
    
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
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">✓ Interview Confirmed</h1>
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
                                            <h3 style="margin: 0 0 15px 0; color: #065f46; font-size: 18px;">📅 Interview Details</h3>
                                            <p style="margin: 0 0 12px 0; color: #047857; font-size: 14px;">
                                                <strong>Date & Time:</strong><br>
                                                <span style="color: #065f46; font-size: 16px;">{slot_time}</span>
                                            </p>
                                            <p style="margin: 0 0 12px 0; color: #047857; font-size: 14px;">
                                                <strong>Duration:</strong><br>
                                                <span style="color: #065f46;">{slot.duration} minutes</span>
                                            </p>
                                            {f'<p style="margin: 0; color: #047857; font-size: 14px;"><strong>Location:</strong><br><span style="color: #065f46;">{slot.location}</span></p>' if slot.location else ''}
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Tips Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #eff6ff; border-radius: 8px; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #1e40af; font-size: 14px;">
                                                💡 <strong>Tip:</strong> Please arrive 5-10 minutes early. Good luck!
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #64748b; font-size: 14px; margin: 0 0 20px 0;">
                                    We look forward to meeting you!
                                </p>
                                
                                <p style="color: #94a3b8; font-size: 13px; margin: 0; line-height: 1.5;">
                                    This is an automated confirmation from {club_name} recruitment system.
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                    Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488; text-decoration: none;">{support_email}</a>
                                </p>
                                <p style="margin: 0 0 12px 0; color: #94a3b8; font-size: 12px;">
                                    © 2025 {club_name}. All rights reserved.
                                </p>
                                <p style="margin: 0; color: #cbd5e1; font-size: 11px;">
                                    You are receiving this email because you booked an interview slot with {club_name}.
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
                            <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 40px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">Password Reset</h1>
                                <p style="color: #94a3b8; margin: 10px 0 0 0; font-size: 16px;">{club_name}</p>
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
                                            <a href="{reset_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%); color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">Reset Password</a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <!-- Info Box -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef3c7; border-radius: 8px; margin: 0 0 30px 0;">
                                    <tr>
                                        <td style="padding: 16px;">
                                            <p style="margin: 0; color: #92400e; font-size: 14px;">
                                                ⏰ This link will expire in 1 hour for security reasons.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #64748b; font-size: 14px; margin: 0 0 10px 0;">
                                    If you didn't request a password reset, please ignore this email or contact support if you have concerns.
                                </p>
                                
                                <p style="color: #94a3b8; font-size: 13px; margin: 0 0 20px 0;">
                                    Or copy and paste this URL into your browser:<br>
                                    <a href="{reset_url}" style="color: #0d9488; word-break: break-all; text-decoration: none;">{reset_url}</a>
                                </p>
                                
                                <p style="color: #94a3b8; font-size: 13px; margin: 0; line-height: 1.5;">
                                    This is an automated security notification from {club_name}.
                                </p>
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                    Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488; text-decoration: none;">{support_email}</a>
                                </p>
                                <p style="margin: 0 0 12px 0; color: #94a3b8; font-size: 12px;">
                                    © 2025 {club_name}. All rights reserved.
                                </p>
                                <p style="margin: 0; color: #cbd5e1; font-size: 11px;">
                                    You are receiving this email because you requested a password reset for your {club_name} account.
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


def send_announcement_email(announcement, candidates):
    """Send announcement to multiple candidates with professional design"""
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    support_email = current_app.config.get('SUPPORT_EMAIL', 'support@techclub.com')
    
    subject = f"[{club_name}] {announcement.title}"
    
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
                                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">📢 {announcement.title}</h1>
                                    <p style="color: #94a3b8; margin: 10px 0 0 0; font-size: 16px;">{club_name}</p>
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
                                                    {announcement.content}
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="color: #64748b; font-size: 14px; margin: 0 0 20px 0;">
                                        Stay tuned for more updates!
                                    </p>
                                    
                                    <p style="color: #94a3b8; font-size: 13px; margin: 0; line-height: 1.5;">
                                        This is an important announcement from {club_name} recruitment team.
                                    </p>
                                </td>
                            </tr>
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8fafc; padding: 24px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                    <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px;">
                                        Need help? Contact us at <a href="mailto:{support_email}" style="color: #0d9488; text-decoration: none;">{support_email}</a>
                                    </p>
                                    <p style="margin: 0 0 12px 0; color: #94a3b8; font-size: 12px;">
                                        © 2025 {club_name}. All rights reserved.
                                    </p>
                                    <p style="margin: 0; color: #cbd5e1; font-size: 11px;">
                                        You are receiving this announcement because you are registered for {club_name} recruitment.
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
