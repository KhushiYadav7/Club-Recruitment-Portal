"""Candidate routes"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.candidate import candidate_bp
from app.candidate.utils import candidate_required
from app import db
from app.models import InterviewSlot, SlotBooking, Announcement
from app.utils.email import send_slot_confirmation_email
from app.utils.audit import log_audit
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@candidate_bp.route('/dashboard')
@login_required
@candidate_required
def dashboard():
    """Candidate dashboard"""
    # Get active announcements
    announcements = Announcement.query.filter_by(is_active=True).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()
    
    # Get candidate's booking if exists
    booking = SlotBooking.query.filter_by(user_id=current_user.id).first()
    
    # Get available slots (future dates only)
    today = datetime.now().date()
    available_slots = InterviewSlot.query.filter(
        InterviewSlot.is_open == True,
        InterviewSlot.date >= today,
        InterviewSlot.current_bookings < InterviewSlot.capacity
    ).order_by(InterviewSlot.date, InterviewSlot.start_time).all()
    
    return render_template('candidate/dashboard.html',
                         announcements=announcements,
                         booking=booking,
                         available_slots=available_slots,
                         application=current_user.application)


@candidate_bp.route('/slots')
@login_required
@candidate_required
def view_slots():
    """View all available interview slots"""
    # Check if candidate already has a booking
    existing_booking = SlotBooking.query.filter_by(user_id=current_user.id).first()
    
    # Get available slots (future dates only)
    today = datetime.now().date()
    
    # Get date filter if provided
    date_filter = request.args.get('date', '')
    
    query = InterviewSlot.query.filter(InterviewSlot.date >= today)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=filter_date)
        except ValueError:
            pass
    
    slots = query.order_by(InterviewSlot.date, InterviewSlot.start_time).all()
    
    # Group slots by date
    slots_by_date = {}
    for slot in slots:
        date_key = slot.date
        if date_key not in slots_by_date:
            slots_by_date[date_key] = []
        slots_by_date[date_key].append(slot)
    
    return render_template('candidate/slots.html',
                         slots_by_date=slots_by_date,
                         existing_booking=existing_booking,
                         date_filter=date_filter)


@candidate_bp.route('/book-slot/<int:slot_id>', methods=['POST'])
@login_required
@candidate_required
def book_slot(slot_id):
    """Book an interview slot with optimistic locking for race condition handling"""
    # Check if candidate already has a slot
    existing_booking = SlotBooking.query.filter_by(user_id=current_user.id).first()
    
    if existing_booking:
        flash('You have already booked a slot. Cancel it first to book a new one.', 'warning')
        return redirect(url_for('candidate.dashboard'))
    
    try:
        # Use database-level locking to prevent race conditions
        slot = InterviewSlot.query.with_for_update().get(slot_id)
        
        if not slot:
            flash('Slot not found', 'danger')
            return redirect(url_for('candidate.view_slots'))
        
        # Double-check availability (prevents race condition)
        if not slot.is_open:
            flash('This slot is no longer open for booking.', 'warning')
            return redirect(url_for('candidate.view_slots'))
        
        if slot.current_bookings >= slot.capacity:
            flash('Sorry, this slot was just booked by someone else. Please select a different slot.', 'warning')
            return redirect(url_for('candidate.view_slots'))
        
        # Check if slot is in the past
        now = datetime.now()
        slot_datetime = datetime.combine(slot.date, slot.start_time)
        
        if slot_datetime < now:
            flash('Cannot book a slot in the past', 'warning')
            return redirect(url_for('candidate.view_slots'))
        
        # Create booking
        booking = SlotBooking(
            slot_id=slot_id,
            user_id=current_user.id,
            confirmed=True
        )
        
        db.session.add(booking)
        
        # Increment slot booking counter and version (optimistic locking)
        slot.current_bookings += 1
        slot.version += 1
        
        # Update application status
        if current_user.application:
            current_user.application.status = 'slot_selected'
        
        db.session.commit()
        
        # Send confirmation email and SMS
        try:
            send_slot_confirmation_email(current_user, slot)
            
            # Send SMS confirmation
            from app.utils.sms import send_slot_confirmation_sms
            send_slot_confirmation_sms(current_user, slot)
        except Exception as e:
            logger.error(f"Failed to send confirmation: {str(e)}")
        
        flash('Interview slot booked successfully! Check your email/SMS for confirmation.', 'success')
        log_audit(current_user.id, 'BOOK_SLOT', f'Booked slot {slot_id} on {slot.date}')
    
    except IntegrityError:
        db.session.rollback()
        flash('Slot booking failed. The slot may already be full or you already have a booking.', 'danger')
        logger.error(f"Integrity error booking slot {slot_id} for user {current_user.id}")
    
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while booking the slot. Please try again.', 'danger')
        logger.error(f"Error booking slot {slot_id} for user {current_user.id}: {str(e)}")
    
    return redirect(url_for('candidate.dashboard'))


@candidate_bp.route('/cancel-slot', methods=['POST'])
@login_required
@candidate_required
def cancel_slot():
    """Cancel booked interview slot"""
    booking = SlotBooking.query.filter_by(user_id=current_user.id).first()
    
    if not booking:
        flash('No booking found', 'warning')
        return redirect(url_for('candidate.dashboard'))
    
    try:
        # Get slot with lock
        slot = InterviewSlot.query.with_for_update().get(booking.slot_id)
        
        # Check if cancellation is allowed (e.g., not within 24 hours)
        now = datetime.now()
        slot_datetime = datetime.combine(slot.date, slot.start_time)
        hours_until_slot = (slot_datetime - now).total_seconds() / 3600
        
        if hours_until_slot < 24:
            flash('Cannot cancel within 24 hours of the interview', 'warning')
            return redirect(url_for('candidate.dashboard'))
        
        # Decrement slot booking counter
        slot.current_bookings = max(0, slot.current_bookings - 1)
        
        # Update application status
        if current_user.application:
            current_user.application.status = 'pending'
        
        # Delete booking
        db.session.delete(booking)
        db.session.commit()
        
        flash('Slot booking cancelled successfully', 'success')
        log_audit(current_user.id, 'CANCEL_SLOT', f'Cancelled slot {booking.slot_id}')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the slot', 'danger')
        logger.error(f"Error cancelling slot for user {current_user.id}: {str(e)}")
    
    return redirect(url_for('candidate.dashboard'))


@candidate_bp.route('/profile')
@login_required
@candidate_required
def profile():
    """View candidate profile"""
    return render_template('candidate/profile.html',
                         user=current_user,
                         application=current_user.application)


@candidate_bp.route('/profile/update', methods=['POST'])
@login_required
@candidate_required
def update_profile():
    """Update candidate profile"""
    try:
        # Update user info
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.phone = request.form.get('phone', current_user.phone).strip()
        
        # Update application info
        if current_user.application:
            current_user.application.skills = request.form.get('skills', '').strip()
        
        db.session.commit()
        
        flash('Profile updated successfully', 'success')
        log_audit(current_user.id, 'UPDATE_PROFILE', 'User updated profile')
    
    except Exception as e:
        db.session.rollback()
        flash('Error updating profile', 'danger')
        logger.error(f"Error updating profile for user {current_user.id}: {str(e)}")
    
    return redirect(url_for('candidate.profile'))
