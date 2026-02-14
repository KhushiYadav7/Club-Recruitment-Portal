"""Email sending utilities - Using Brevo API with premium professional templates

Brevo Setup:
1. Sign up at https://www.brevo.com (free: 300 emails/day)
2. Go to SMTP & API → API Keys
3. Create an API key with "Send transactional emails" permission
4. Set environment variables:
   - BREVO_API_KEY=your-api-key
   - EMAIL_FROM=your-verified-email
   - EMAIL_FROM_NAME=Your Club Name
   - EMAIL_REPLY_TO=reply-to@email.com
"""
from flask import current_app
import logging
import re
import requests

logger = logging.getLogger(__name__)

# Brevo API endpoint
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def strip_html_to_text(html):
    """Convert HTML to plain text for email"""
    # Remove hidden preheader divs first (they have display:none and max-height:0)
    text = re.sub(r'<div[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n ', '\n', text)
    return text.strip()


def is_email_configured():
    """Check if Brevo is properly configured"""
    api_key = current_app.config.get('BREVO_API_KEY')
    from_email = current_app.config.get('EMAIL_FROM')
    return bool(api_key and from_email)


def send_email(to_email, subject, html_content):
    """Send email using Brevo API"""
    if not is_email_configured():
        logger.warning(f"Brevo not configured. Skipping email to {to_email}")
        return True
    
    try:
        api_key = current_app.config['BREVO_API_KEY']
        from_email = current_app.config.get('EMAIL_FROM', 'noreply@example.com')
        from_name = current_app.config.get('EMAIL_FROM_NAME', current_app.config.get('CLUB_NAME', 'Tech Club'))
        reply_to = current_app.config.get('EMAIL_REPLY_TO', from_email)
        
        text_content = strip_html_to_text(html_content)
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key
        }
        
        payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": to_email}],
            "replyTo": {"email": reply_to, "name": f"{from_name} Support"},
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content
        }
        
        response = requests.post(BREVO_API_URL, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            logger.info(f"Email sent to {to_email}")
            return True
        else:
            logger.warning(f"Brevo returned {response.status_code}: {response.text}")
            return True
        
    except Exception as e:
        logger.warning(f"Email failed to {to_email}: {str(e)}")
        return True


# Premium warm color palette - charcoal + gold
COLORS = {
    'bg': '#1a1a1a',
    'card': '#242424',
    'card_inner': '#2d2d2d',
    'border': '#3d3d3d',
    'gold': '#d4a853',
    'gold_light': '#e8c97a',
    'success': '#4a9d6e',
    'success_bg': 'rgba(74, 157, 110, 0.12)',
    'warning': '#c9963a',
    'warning_bg': 'rgba(201, 150, 58, 0.12)',
    'text': '#f5f5f5',
    'text_secondary': '#b8b8b8',
    'text_muted': '#888888',
}

# Preheader configuration
PREHEADER_PADDING_LENGTH = 100  # Number of non-breaking spaces to add after preheader text


def _base_template(header_bg, header_title, header_sub, body, footer_note, preheader=None):
    """Generate base email template with warm premium styling"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    support = current_app.config.get('SUPPORT_EMAIL', 'support@codescriet.com')
    
    # Generate preheader div if preheader text is provided
    preheader_html = ''
    if preheader:
        padding = '&nbsp;' * PREHEADER_PADDING_LENGTH
        preheader_html = f'<div style="display: none; max-height: 0; overflow: hidden; color: {c["bg"]};">{preheader}{padding}</div>'
    
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
</head>
<body style="margin:0;padding:0;font-family:Georgia,'Times New Roman',serif;background:{c['bg']};">
{preheader_html}
<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['bg']};padding:40px 20px;">
<tr><td align="center">
<table width="580" cellpadding="0" cellspacing="0" style="background:{c['card']};border-radius:8px;border:1px solid {c['border']};">

<!-- Header -->
<tr><td style="background:{header_bg};padding:28px 32px;border-radius:8px 8px 0 0;">
<p style="font-family:'Courier New',monospace;color:{c['gold']};font-size:13px;margin:0 0 6px 0;letter-spacing:1px;">&lt;{club}/&gt;</p>
<h1 style="color:{c['text']};margin:0;font-size:22px;font-weight:normal;">{header_title}</h1>
<p style="color:{c['text_muted']};margin:8px 0 0 0;font-size:14px;">{header_sub}</p>
</td></tr>

<!-- Gold line -->
<tr><td style="background:{c['gold']};height:2px;"></td></tr>

<!-- Body -->
<tr><td style="padding:32px;background:{c['card_inner']};">
{body}
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 32px;text-align:center;border-top:1px solid {c['border']};">
<p style="margin:0 0 6px 0;color:{c['text_muted']};font-size:12px;">Questions? Reach us at <a href="mailto:{support}" style="color:{c['gold']};">{support}</a></p>
<p style="margin:0;color:{c['text_muted']};font-size:11px;">{footer_note}</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''


def send_credentials_email(user, temp_password):
    """Send login credentials"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    login_url = f"{base_url}/auth/login"
    
    subject = f"{user.name}, your login details for {club}"
    
    body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {user.name},</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 24px 0;line-height:1.6;">
Your account is ready. Here are your login details:
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['card']};border-radius:6px;border-left:3px solid {c['gold']};margin:0 0 24px 0;">
<tr><td style="padding:20px;">
<p style="margin:0 0 10px 0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Portal:</strong><br>
<a href="{login_url}" style="color:{c['gold']};">{login_url}</a>
</p>
<p style="margin:0 0 10px 0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Email:</strong><br>{user.email}
</p>
<p style="margin:0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Password:</strong><br>
<code style="background:{c['bg']};padding:4px 10px;border-radius:4px;font-family:monospace;color:{c['gold_light']};font-size:15px;">{temp_password}</code>
</p>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['warning_bg']};border-radius:4px;border:1px solid rgba(201,150,58,0.25);margin:0 0 24px 0;">
<tr><td style="padding:12px 16px;">
<p style="margin:0;color:{c['warning']};font-size:13px;">Please change your password after your first login.</p>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center">
<a href="{login_url}" style="display:inline-block;padding:12px 28px;background:{c['gold']};color:{c['bg']};text-decoration:none;border-radius:4px;font-weight:bold;font-size:14px;">Sign In</a>
</td></tr>
</table>
'''
    
    html = _base_template(c['card'], "Your Account is Ready", "Recruitment Portal", body, f"You registered for {club} recruitment.", preheader=f"Your {club} account is ready. Login details inside.")
    return send_email(user.email, subject, html)


def send_admin_credentials_email(user, temp_password):
    """Send admin login credentials"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    login_url = f"{base_url}/auth/login"
    
    subject = f"{user.name}, admin access granted - {club}"
    
    body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {user.name},</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 24px 0;line-height:1.6;">
You now have admin access to the {club} portal.
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['card']};border-radius:6px;border-left:3px solid {c['gold']};margin:0 0 24px 0;">
<tr><td style="padding:20px;">
<p style="margin:0 0 10px 0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Portal:</strong><br>
<a href="{login_url}" style="color:{c['gold']};">{login_url}</a>
</p>
<p style="margin:0 0 10px 0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Email:</strong><br>{user.email}
</p>
<p style="margin:0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Password:</strong><br>
<code style="background:{c['bg']};padding:4px 10px;border-radius:4px;font-family:monospace;color:{c['gold_light']};font-size:15px;">{temp_password}</code>
</p>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['warning_bg']};border-radius:4px;border:1px solid rgba(201,150,58,0.25);margin:0 0 24px 0;">
<tr><td style="padding:12px 16px;">
<p style="margin:0;color:{c['warning']};font-size:13px;">Change your password on first login.</p>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center">
<a href="{login_url}" style="display:inline-block;padding:12px 28px;background:{c['gold']};color:{c['bg']};text-decoration:none;border-radius:4px;font-weight:bold;font-size:14px;">Access Admin Panel</a>
</td></tr>
</table>
'''
    
    html = _base_template(c['card'], "Admin Access Granted", club, body, f"You were granted admin access to {club}.", preheader=f"Admin access granted for {club}.")
    return send_email(user.email, subject, html)


def send_slot_confirmation_email(user, slot):
    """Send interview slot confirmation"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    
    from datetime import datetime
    slot_date = slot.date.strftime('%A, %B %d')
    time_range = f"{slot.start_time.strftime('%I:%M %p')} – {slot.end_time.strftime('%I:%M %p')}"
    
    subject = f"{user.name}, interview confirmed for {slot.date.strftime('%b %d')}"
    
    body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {user.name},</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 24px 0;line-height:1.6;">
Your interview slot is confirmed. Details below:
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['card']};border-radius:6px;border-left:3px solid {c['success']};margin:0 0 24px 0;">
<tr><td style="padding:20px;">
<p style="margin:0 0 10px 0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Date:</strong><br>
<span style="color:{c['text']};font-size:15px;">{slot_date}</span>
</p>
<p style="margin:0;color:{c['text_muted']};font-size:13px;">
<strong style="color:{c['text']};">Time:</strong><br>
<span style="color:{c['text']};">{time_range}</span>
</p>
</td></tr>
</table>

<p style="color:{c['text_muted']};font-size:13px;margin:0;line-height:1.5;">
Please arrive a few minutes early. We look forward to meeting you.
</p>
'''
    
    html = _base_template(f"linear-gradient(135deg, #2d4a3e 0%, {c['card']} 100%)", "Interview Confirmed", "Your slot is booked", body, f"You booked an interview with {club}.", preheader=f"Your interview slot is confirmed for {slot_date}.")
    return send_email(user.email, subject, html)


def send_password_reset_email(user, reset_token):
    """Send password reset link"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    reset_url = f"{base_url}/auth/reset-password/{reset_token}"
    
    subject = f"{user.name}, password reset for {club}"
    
    body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {user.name},</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 24px 0;line-height:1.6;">
We received a request to reset your password. Click below to set a new one:
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">
<tr><td align="center">
<a href="{reset_url}" style="display:inline-block;padding:12px 28px;background:{c['gold']};color:{c['bg']};text-decoration:none;border-radius:4px;font-weight:bold;font-size:14px;">Reset Password</a>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['warning_bg']};border-radius:4px;border:1px solid rgba(201,150,58,0.25);margin:0 0 24px 0;">
<tr><td style="padding:12px 16px;">
<p style="margin:0;color:{c['warning']};font-size:13px;">This link expires in 1 hour.</p>
</td></tr>
</table>

<p style="color:{c['text_muted']};font-size:12px;margin:0;line-height:1.5;">
If you didn't request this, ignore this email. Your account is safe.
</p>
'''
    
    html = _base_template(c['card'], "Reset Your Password", club, body, f"You requested a password reset for {club}.", preheader=f"Reset your {club} password securely.")
    return send_email(user.email, subject, html)


def send_announcement_email(candidates, title, content):
    """Send announcement to candidates"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    
    success = 0
    failed = 0
    
    for candidate in candidates:
        subject = f"{candidate.name}, update from {club}"
        
        body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {candidate.name},</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['card']};border-radius:6px;border-left:3px solid {c['gold']};margin:0 0 20px 0;">
<tr><td style="padding:20px;">
<div style="color:{c['text_secondary']};font-size:14px;line-height:1.7;">{content}</div>
</td></tr>
</table>
'''
        
        html = _base_template(c['card'], title, f"{club} Update", body, f"You're receiving this as a {club} applicant.", preheader=f"Important: {title} — from {club}")
        
        if send_email(candidate.email, subject, html):
            success += 1
        else:
            failed += 1
    
    return success, failed


def send_selection_email(user):
    """Send selection notification"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    
    subject = f"Congratulations {user.name} — Welcome to {club}"
    
    body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {user.name},</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 20px 0;line-height:1.6;">
We're pleased to inform you that you've been selected to join <strong style="color:{c['text']};">{club}</strong>.
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['success_bg']};border-radius:6px;border:1px solid rgba(74,157,110,0.25);margin:0 0 24px 0;">
<tr><td style="padding:20px;text-align:center;">
<p style="color:{c['success']};font-size:18px;font-weight:bold;margin:0;">You're in.</p>
</td></tr>
</table>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 16px 0;line-height:1.6;">
Here's what happens next:
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">
<tr><td style="padding:12px 16px;background:{c['card']};border-radius:4px;">
<p style="margin:0;color:{c['text']};font-size:14px;"><strong>WhatsApp</strong> — You'll be added to our team groups</p>
</td></tr>
<tr><td style="height:8px;"></td></tr>
<tr><td style="padding:12px 16px;background:{c['card']};border-radius:4px;">
<p style="margin:0;color:{c['text']};font-size:14px;"><strong>Website</strong> — Your profile goes live as a member</p>
</td></tr>
<tr><td style="height:8px;"></td></tr>
<tr><td style="padding:12px 16px;background:{c['card']};border-radius:4px;">
<p style="margin:0;color:{c['text']};font-size:14px;"><strong>Discord</strong> — Join via the website for discussions</p>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px 0;">
<tr><td align="center">
<a href="{base_url}" style="display:inline-block;padding:12px 28px;background:{c['success']};color:#fff;text-decoration:none;border-radius:4px;font-weight:bold;font-size:14px;">Visit Website</a>
</td></tr>
</table>

<p style="color:{c['text_muted']};font-size:13px;margin:0;line-height:1.5;">
Welcome aboard. We're excited to work with you.
</p>
'''
    
    html = _base_template(f"linear-gradient(135deg, #2d4a3e 0%, {c['card']} 100%)", "You've Been Selected", "Welcome to the team", body, f"You applied for {club} recruitment.", preheader=f"Congratulations! You've been selected to join {club}.")
    return send_email(user.email, subject, html)


def send_rejection_email(user):
    """Send rejection notification"""
    c = COLORS
    club = current_app.config.get('CLUB_NAME', 'code.scriet')
    
    subject = f"{user.name}, regarding your {club} application"
    
    body = f'''
<p style="color:{c['text']};font-size:15px;margin:0 0 16px 0;line-height:1.5;">Hello {user.name},</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 20px 0;line-height:1.6;">
Thank you for taking the time to apply and interview with us. We appreciate your interest in {club}.
</p>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 24px 0;line-height:1.6;">
After careful consideration, we've decided not to move forward with your application at this time. This was a competitive process with many strong candidates.
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['card']};border-radius:6px;border-left:3px solid {c['warning']};margin:0 0 24px 0;">
<tr><td style="padding:20px;">
<p style="color:{c['text']};font-size:14px;font-weight:bold;margin:0 0 12px 0;">A few suggestions:</p>
<ul style="color:{c['text_secondary']};font-size:13px;line-height:1.8;margin:0;padding-left:18px;">
<li>Strengthen your core fundamentals</li>
<li>Build personal projects to demonstrate skills</li>
<li>Stay active in coding challenges and communities</li>
</ul>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="background:{c['success_bg']};border-radius:4px;border:1px solid rgba(74,157,110,0.2);margin:0 0 24px 0;">
<tr><td style="padding:14px 16px;text-align:center;">
<p style="margin:0;color:{c['success']};font-size:13px;">You're welcome to apply again in our next recruitment round.</p>
</td></tr>
</table>

<p style="color:{c['text_secondary']};font-size:14px;margin:0 0 16px 0;line-height:1.6;">
We wish you the best in your journey ahead.
</p>

<p style="color:{c['text']};font-size:14px;margin:0;">
Regards,<br>
<span style="color:{c['gold']};">The {club} Team</span>
</p>
'''
    
    html = _base_template(c['card'], "Thank You for Applying", "Application Update", body, f"You applied for {club} recruitment.", preheader=f"An update regarding your {club} application.")
    return send_email(user.email, subject, html)
