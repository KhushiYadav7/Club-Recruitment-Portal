# Email Templates & Deliverability Guide (Brevo)

**Last Updated:** February 5, 2026

This document explains the email template system, required API keys/config, and how to ensure emails land in Primary instead of Promotions.

---

## 1) Email Service Provider

**Provider:** Brevo (formerly Sendinblue)  
**API Endpoint:** `https://api.brevo.com/v3/smtp/email`

The system uses Brevo transactional emails for:
- Welcome emails & login credentials
- Event registrations, reminders, and announcements
- Password reset
- Hiring applications
- **Selection notifications** (congratulations email)
- **Rejection notifications** (encouraging feedback email)

---

## 2) Required Environment Variables

Set these in the backend environment (Render/production or `.env` locally):

| Variable | Description | Default |
|----------|-------------|---------|
| `BREVO_API_KEY` | Brevo API key for sending emails | *Required* |
| `EMAIL_FROM` | From-address shown to users | `noreply@codescriet.dev` |
| `EMAIL_FROM_NAME` | From-name shown to users | `code.scriet` |
| `EMAIL_REPLY_TO` | Reply-to address | `support@codescriet.com` |

---

## 3) Template Engine & Structure

### 3.1 Core Files
All templates are built in [app/utils/email.py](file:///Users/lakshya/Developement/hiring_sys_club/app/utils/email.py).

### 3.2 Available Functions

| Function | Purpose |
|----------|---------|
| `send_email(to, subject, html)` | Core sender using Brevo API |
| `send_credentials_email(user, password)` | Login credentials for candidates |
| `send_admin_credentials_email(user, password)` | Admin account credentials |
| `send_slot_confirmation_email(user, slot)` | Interview slot booking |
| `send_password_reset_email(user, token)` | Password reset link |
| `send_announcement_email(candidates, title, content)` | Bulk announcements |
| `send_selection_email(user)` | 🎉 Congratulations + WhatsApp/Discord info |
| `send_rejection_email(user)` | Encouraging rejection + reapply guidance |

### 3.3 Visual Design
**Brand feel:** Warm, premium, sophisticated.

| Element | Value |
|---------|-------|
| Background | `#1a1a1a` (warm charcoal) |
| Card | `#242424` |
| Accent (gold) | `#d4a853` |
| Success | `#4a9d6e` (warm green) |
| Warning | `#c9963a` (amber) |

**Typography:** Georgia serif for elegance, monospace for code.

---

## 4) Keeping Emails in the Primary Inbox

### ✅ Authentication & Domain Setup
1. **SPF**: Add Brevo's SPF record to DNS
2. **DKIM**: Enable in Brevo settings
3. **DMARC**: Start with `p=none`
4. **Consistent sender**: Same "From" name/address

### ✅ Content Best Practices (Already Applied)
- Personal subjects with recipient name
- Text-forward design (not image-heavy)
- Single primary CTA per email
- Plain text version auto-generated
- No promotional keywords ("FREE", "LIMITED OFFER")

### ✅ User-Level Tips
Ask members to:
- Add sender to contacts
- Move to Primary if it lands elsewhere
- Reply once to train inbox

---

## 5) Usage Examples

### Send Selection Email
```python
from app.utils.email import send_selection_email

# After marking candidate as selected
send_selection_email(user)
```

### Send Rejection Email
```python
from app.utils.email import send_rejection_email

# After marking candidate as rejected
send_rejection_email(user)
```

### Send Announcement
```python
from app.utils.email import send_announcement_email

candidates = User.query.filter_by(role='candidate').all()
success, failed = send_announcement_email(candidates, "Important Update", "Content here...")
```

---

## 6) Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Emails not sending | Check `BREVO_API_KEY` in env |
| Emails in Promotions | Verify DKIM/SPF, reduce promo language |
| Broken links | Ensure `BASE_URL` is correct |

---

## 7) Security Notes

- Never commit API keys to git
- Use server-side env vars only
- Restrict Brevo API key to **SMTP Send** permission only
