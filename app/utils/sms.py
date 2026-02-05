"""SMS sending utilities - Using Fast2SMS API

Fast2SMS Setup:
1. Sign up at https://fast2sms.com
2. Verify with OTP
3. Go to Dashboard → Dev API
4. Copy your API Authorization Key
5. Set environment variable:
   - FAST2SMS_API_KEY=your-api-key
   
Works on localhost! No domain verification needed.
Free tier: ~10 SMS for testing
"""
import requests
from flask import current_app
import logging

logger = logging.getLogger(__name__)

FAST2SMS_API_URL = "https://www.fast2sms.com/dev/bulkV2"


def is_sms_configured():
    """Check if Fast2SMS is properly configured"""
    api_key = current_app.config.get('FAST2SMS_API_KEY')
    return bool(api_key)


def format_phone_number(phone):
    """Format phone number for Fast2SMS (10 digits, no country code)"""
    if not phone:
        return None
    
    # Remove all non-digits
    phone = ''.join(filter(str.isdigit, str(phone)))
    
    # Remove country code if present (91 for India)
    if len(phone) == 12 and phone.startswith('91'):
        phone = phone[2:]
    elif len(phone) == 11 and phone.startswith('0'):
        phone = phone[1:]
    
    # Validate 10-digit Indian number
    if len(phone) != 10:
        logger.warning(f"Invalid phone number format: {phone}")
        return None
    
    return phone


def send_sms(to_phone, message):
    """Send SMS using Fast2SMS API
    
    Args:
        to_phone: Phone number (10 digits or with country code)
        message: Message content (max 160 chars for single SMS)
    
    Returns:
        bool: True always (never blocks workflow)
    """
    if not is_sms_configured():
        logger.warning(f"Fast2SMS not configured. Skipping SMS to {to_phone}")
        return True
    
    phone = format_phone_number(to_phone)
    if not phone:
        logger.warning(f"Invalid phone number: {to_phone}")
        return True
    
    try:
        api_key = current_app.config['FAST2SMS_API_KEY']
        route = current_app.config.get('FAST2SMS_ROUTE', 'q')
        
        headers = {
            'authorization': api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'route': route,
            'message': message,
            'language': 'english',
            'flash': 0,
            'numbers': phone
        }
        
        response = requests.post(FAST2SMS_API_URL, headers=headers, json=payload)
        result = response.json()
        
        if result.get('return'):
            logger.info(f"SMS sent to {phone}: {result.get('request_id', 'N/A')}")
            return True
        else:
            logger.warning(f"Fast2SMS error: {result.get('message', 'Unknown error')}")
            return True  # Don't block workflow
        
    except Exception as e:
        logger.warning(f"SMS failed to {to_phone}: {str(e)}")
        return True  # Never block workflow


def send_credentials_sms(user, temp_password):
    """Send login credentials via SMS"""
    if not user.phone:
        return True
    
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    
    # Keep message concise for SMS (160 char limit for single SMS)
    message = f"""Welcome to {club_name}!

Login: {base_url}/auth/login
Email: {user.email}
Password: {temp_password}

Change password after first login."""
    
    return send_sms(user.phone, message)


def send_admin_credentials_sms(user, temp_password):
    """Send admin login credentials via SMS"""
    if not user.phone:
        return True
    
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    
    message = f"""Admin Access Granted - {club_name}

Login: {base_url}/auth/login
Email: {user.email}
Password: {temp_password}

Change password on first login."""
    
    return send_sms(user.phone, message)


def send_slot_confirmation_sms(user, slot):
    """Send slot booking confirmation via SMS"""
    if not user.phone:
        return True
    
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    
    # Format date and time
    date_str = slot.date.strftime('%d %b %Y')
    time_str = slot.start_time.strftime('%I:%M %p')
    
    message = f"""Interview Confirmed - {club_name}

Date: {date_str}
Time: {time_str}

Please arrive 10 mins early. Good luck!"""
    
    return send_sms(user.phone, message)


def send_announcement_sms(candidates, title, content):
    """Send announcement to multiple candidates via SMS
    
    Args:
        candidates: List of User objects
        title: Announcement title
        content: Announcement content
    
    Returns:
        tuple: (success_count, failed_count)
    """
    club_name = current_app.config.get('CLUB_NAME', 'Tech Club')
    success = 0
    failed = 0
    
    # Truncate content for SMS (keep under 160 chars total)
    max_content_len = 100
    if len(content) > max_content_len:
        content = content[:max_content_len-3] + "..."
    
    for candidate in candidates:
        if candidate.phone:
            message = f"""{club_name} Update

{title}

{content}"""
            
            if send_sms(candidate.phone, message):
                success += 1
            else:
                failed += 1
    
    return success, failed
