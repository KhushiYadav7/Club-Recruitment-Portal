# Technical Recruitment Management System

A production-grade recruitment management web application built with **Python Flask + PostgreSQL + Bootstrap 5** for university clubs and organizations.

## 🎯 Features

- **Role-Based Access Control**
  - Admin dashboard with comprehensive management tools
  - Candidate self-service portal

- **Authentication & Security**
  - Secure login with account lockout protection
  - Forced password change on first login
  - CSRF protection
  - Rate limiting on sensitive endpoints
  - Audit logging for admin actions

- **Candidate Management**
  - Bulk upload via Excel/CSV
  - Automatic credential generation and email delivery
  - Application status tracking
  - Profile management

- **Interview Scheduling**
  - Self-service slot booking system
  - Real-time availability updates
  - Race condition prevention with database locking
  - Email confirmations
  - Capacity management

- **Communication**
  - System-wide announcements
  - Email notifications
  - Automated credential delivery

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL 12+ (or SQLite for development)
- SMTP server for email (Gmail, SendGrid, etc.)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd hiring_sys_club

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Important configurations in `.env`:**
```env
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=postgresql://user:password@localhost/recruitment_db

# Email Settings (example with Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# App Settings
CLUB_NAME=code.scriet
SUPPORT_EMAIL=support@codescriet.com
BASE_URL=http://localhost:5000
```

### 3. Initialize Database

```bash
# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Or use the CLI command
python run.py init_db
```

### 4. Create Admin User

```bash
python run.py create_admin
```

Follow the prompts to create your first admin account.

### 5. Run the Application

```bash
# Development mode
python run.py

# Or use Flask CLI
flask run
```

The application will be available at `http://localhost:5000`

## 📁 Project Structure

```
recruitment-system/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # Database models
│   ├── routes.py                # Main routes
│   ├── auth/                    # Authentication blueprint
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── utils.py
│   ├── admin/                   # Admin blueprint
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── utils.py
│   ├── candidate/               # Candidate blueprint
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── utils.py
│   ├── api/                     # REST API
│   │   ├── __init__.py
│   │   └── slots.py
│   ├── utils/                   # Utilities
│   │   ├── email.py
│   │   ├── security.py
│   │   ├── validators.py
│   │   └── audit.py
│   ├── templates/               # HTML templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── admin/
│   │   ├── candidate/
│   │   └── errors/
│   └── static/                  # CSS, JS, images
│       ├── css/
│       └── js/
├── migrations/                   # Database migrations
├── config.py                     # Configuration
├── requirements.txt              # Python dependencies
├── run.py                        # Application entry point
└── README.md                     # This file
```

## 👥 User Roles

### Admin
- Upload candidates in bulk via Excel/CSV
- Create and manage interview slots
- View all candidates and their status
- Update application statuses
- Create announcements
- View audit logs

### Candidate
- View available interview slots
- Book interview slots (one per candidate)
- Cancel bookings (with time restrictions)
- View announcements
- Update profile information
- Change password

## 📤 Bulk Upload Format

Create an Excel or CSV file with the following columns:

| Name       | Email              | Phone      | Department        | Year     | Skills           |
|------------|-------------------|------------|-------------------|----------|------------------|
| John Doe   | john@example.com  | 1234567890 | Computer Science  | 2nd Year | Python, JS       |
| Jane Smith | jane@example.com  | 9876543210 | Electronics       | 3rd Year | C++, Arduino     |

**Required columns:** Name, Email, Department, Year  
**Optional columns:** Phone, Skills

Each candidate will receive an email with their login credentials automatically.

## 🔒 Security Features

1. **Password Security**
   - Bcrypt hashing
   - Minimum complexity requirements
   - Forced change on first login

2. **Account Protection**
   - Account lockout after 5 failed attempts
   - 15-minute lockout duration
   - Session timeout

3. **CSRF Protection**
   - All forms protected with CSRF tokens
   - Secure cookie settings

4. **Rate Limiting**
   - Login endpoint: 10 attempts per minute
   - Password reset: 3 attempts per hour

5. **Audit Logging**
   - All admin actions logged
   - IP address tracking
   - Timestamp recording

## 📧 Email Configuration

### Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password:
   - Go to Google Account Settings
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and "Other" device
   - Copy the generated password

3. Update `.env`:
```env
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-digit-app-password
```

### SendGrid Setup (Alternative)

```python
# In config.py, update mail settings:
MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_PORT = 587
MAIL_USERNAME = 'apikey'
MAIL_PASSWORD = 'your-sendgrid-api-key'
```

## 🗄️ Database Models

- **User**: Stores user accounts (admin and candidates)
- **Application**: Candidate application details
- **InterviewSlot**: Available interview time slots
- **SlotBooking**: Candidate slot bookings
- **Announcement**: System announcements
- **SystemConfig**: Configuration key-value store
- **AuditLog**: Admin action audit trail

## 🔧 Production Deployment

### PostgreSQL Setup

```bash
# Install PostgreSQL
# On Ubuntu:
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE recruitment_db;
CREATE USER recruitment_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE recruitment_db TO recruitment_user;
\q
```

### Environment Variables

Update `.env` for production:
```env
FLASK_ENV=production
SECRET_KEY=generate-a-strong-random-key
DATABASE_URL=postgresql://recruitment_user:password@localhost/recruitment_db
```

### Using Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

### Using Nginx (Recommended)

Create `/etc/nginx/sites-available/recruitment`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/app/static;
    }
}
```

### Systemd Service

Create `/etc/systemd/system/recruitment.service`:
```ini
[Unit]
Description=Recruitment Portal
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/recruitment-system
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 "app:create_app('production')"

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable recruitment
sudo systemctl start recruitment
```

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## 📊 API Endpoints

- `GET /api/slots` - Get all available slots
- `GET /api/slots/<id>` - Get specific slot details
- `GET /api/my-booking` - Get current user's booking
- `GET /api/stats` - Get system statistics (admin only)

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U recruitment_user -d recruitment_db -h localhost
```

### Email Not Sending
- Verify SMTP credentials
- Check firewall rules (port 587)
- Enable "Less secure app access" or use App Passwords
- Check spam folder

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📝 CLI Commands

```bash
# Create admin user
python run.py create_admin

# Initialize database
python run.py init_db

# Open Flask shell with context
flask shell
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Support

For issues or questions:
- Email: {{ SUPPORT_EMAIL }}
- Create an issue on GitHub

## 🔄 Version History

- **v1.0.0** (2025-01-01)
  - Initial release
  - Basic authentication and authorization
  - Candidate management
  - Interview scheduling
  - Email notifications
  - Admin dashboard

## 🎯 Future Enhancements

- [ ] SMS notifications
- [ ] Calendar integration (Google Calendar, Outlook)
- [ ] Interview feedback forms
- [ ] Document upload for candidates
- [ ] Advanced analytics and reporting
- [ ] Multi-round interview support
- [ ] Video interview integration
- [ ] Mobile app

---

**Built with ❤️ for university clubs and organizations**
