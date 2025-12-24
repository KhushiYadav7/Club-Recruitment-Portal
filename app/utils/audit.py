"""Audit logging utilities"""
from app import db
from app.models import AuditLog
from flask import request
import logging

logger = logging.getLogger(__name__)


def log_audit(user_id, action, details=None):
    """Log an audit event - uses existing transaction for efficiency
    
    Args:
        user_id (int): ID of the user performing the action
        action (str): Action being performed
        details (str): Additional details about the action
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else None
        )
        db.session.add(audit_log)
        # Commit with existing transaction - reduces DB round trips
        db.session.commit()
        logger.info(f"Audit: User {user_id} - {action}")
    except Exception as e:
        logger.warning(f"Failed to log audit (non-critical): {str(e)}")
        try:
            db.session.rollback()
        except:
            pass  # Don't fail if rollback fails
