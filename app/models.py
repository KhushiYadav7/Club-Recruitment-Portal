"""Database models for recruitment system"""
from datetime import datetime
from app import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    """User model for both admins and candidates"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'candidate', name='user_roles'), default='candidate')
    first_login = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - use lazy='select' (default) for on-demand loading
    application = db.relationship('Application', backref='user', uselist=False, cascade='all, delete-orphan', lazy='select')
    slot_booking = db.relationship('SlotBooking', backref='user', uselist=False, cascade='all, delete-orphan', lazy='select')
    created_slots = db.relationship('InterviewSlot', foreign_keys='InterviewSlot.created_by', backref='creator', lazy='dynamic')
    created_announcements = db.relationship('Announcement', foreign_keys='Announcement.created_by', backref='creator', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Application(db.Model):
    """Candidate application details"""
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    department = db.Column(db.String(100))
    year = db.Column(db.String(20))
    skills = db.Column(db.Text)
    status = db.Column(
        db.Enum('pending', 'slot_selected', 'interviewed', 'selected', 'rejected', name='application_status'),
        default='pending',
        index=True  # Index for status filtering
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.user.name} - {self.status}>'


class InterviewSlot(db.Model):
    """Interview time slots that candidates can book"""
    __tablename__ = 'interview_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)  # Index for date filtering
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, default=1)
    current_bookings = db.Column(db.Integer, default=0)
    is_open = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bookings = db.relationship('SlotBooking', backref='slot', cascade='all, delete-orphan')
    
    @property
    def is_full(self):
        """Check if slot is at capacity"""
        return self.current_bookings >= self.capacity
    
    @property
    def is_available(self):
        """Check if slot is available for booking"""
        return self.is_open and not self.is_full
    
    @property
    def available_spots(self):
        """Get number of available spots"""
        return max(0, self.capacity - self.current_bookings)
    
    def __repr__(self):
        return f'<InterviewSlot {self.date} {self.start_time}-{self.end_time}>'


class SlotBooking(db.Model):
    """Candidate slot bookings"""
    __tablename__ = 'slot_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('interview_slots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', name='one_slot_per_user'),
    )
    
    def __repr__(self):
        return f'<SlotBooking {self.user.name} -> Slot {self.slot_id}>'


class Announcement(db.Model):
    """System announcements for candidates"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


class SystemConfig(db.Model):
    """System configuration key-value store"""
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_value(key, default=None):
        """Get configuration value"""
        config = SystemConfig.query.filter_by(key=key).first()
        return config.value if config else default
    
    @staticmethod
    def set_value(key, value):
        """Set configuration value"""
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = value
        else:
            config = SystemConfig(key=key, value=value)
            db.session.add(config)
        db.session.commit()
    
    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'


class AuditLog(db.Model):
    """Audit log for tracking admin actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id}>'


class PasswordResetToken(db.Model):
    """Password reset tokens"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('reset_tokens', cascade='all, delete-orphan'))
    
    @property
    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def __repr__(self):
        return f'<PasswordResetToken for User {self.user_id}>'
