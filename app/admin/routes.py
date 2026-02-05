"""Admin routes"""
from flask import render_template, redirect, url_for, flash, request, jsonify, Response, current_app
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.admin.utils import admin_required, parse_excel_file, validate_candidate_data, super_admin_required
from app import db
from app.models import User, Application, InterviewSlot, SlotBooking, Announcement, AuditLog
from app.auth.utils import create_candidate
from app.utils.validators import allowed_file
from app.utils.audit import log_audit
from app.utils.email import send_credentials_email, send_announcement_email
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with comprehensive overview statistics"""
    try:
        now = datetime.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        
        # Basic candidate statistics
        total_candidates = User.query.filter_by(role='candidate').count()
        active_candidates = User.query.filter_by(role='candidate', is_active=True).count()
        
        # Recent candidates (added in last 7 days)
        recent_candidates = User.query.filter(
            User.role == 'candidate',
            User.created_at >= week_ago
        ).count()
        
        # Slot statistics
        total_slots = InterviewSlot.query.count()
        active_slots = InterviewSlot.query.filter_by(is_open=True).filter(
            InterviewSlot.date >= today
        ).count()
        
        # Booking statistics - SlotBooking uses 'confirmed' boolean, not 'status' string
        total_bookings = SlotBooking.query.count()
        confirmed_bookings = SlotBooking.query.filter_by(confirmed=True).count()
        cancelled_bookings = SlotBooking.query.filter_by(confirmed=False).count()
        
        # Calculate total slot capacity
        total_capacity = db.session.query(func.sum(InterviewSlot.capacity)).scalar() or 0
        total_booked = db.session.query(func.sum(InterviewSlot.current_bookings)).scalar() or 0
        capacity_percentage = round((total_booked / total_capacity * 100) if total_capacity > 0 else 0)
        
        # Department-wise breakdown with booking info
        dept_query = db.session.query(
            Application.department,
            func.count(Application.id).label('count')
        ).group_by(Application.department).all()
        
        dept_stats = []
        for dept, count in dept_query:
            # Count how many in this department have booked (confirmed=True)
            booked = db.session.query(func.count(SlotBooking.id)).join(
                User, SlotBooking.user_id == User.id
            ).join(
                Application, Application.user_id == User.id
            ).filter(
                Application.department == dept,
                SlotBooking.confirmed == True
            ).scalar() or 0
            dept_stats.append({
                'department': dept,
                'count': count,
                'booked': booked
            })
        
        # Status-wise breakdown
        status_query = db.session.query(
            Application.status,
            func.count(Application.id).label('count')
        ).group_by(Application.status).all()
        
        status_stats = [{'status': status, 'count': count} for status, count in status_query]
        
        # Upcoming interviews (slots) with booked count
        upcoming_slots = InterviewSlot.query.filter(
            InterviewSlot.date >= today
        ).order_by(InterviewSlot.date, InterviewSlot.start_time).all()
        
        # Add booked_count attribute for template
        for slot in upcoming_slots:
            slot.booked_count = slot.current_bookings
        
        # Recent bookings with full details for display
        raw_recent_bookings = SlotBooking.query.join(
            User, SlotBooking.user_id == User.id
        ).join(
            InterviewSlot, SlotBooking.slot_id == InterviewSlot.id
        ).order_by(SlotBooking.booked_at.desc()).limit(10).all()
        
        recent_bookings = []
        for booking in raw_recent_bookings:
            user = User.query.get(booking.user_id)
            slot = InterviewSlot.query.get(booking.slot_id)
            if user and slot:
                recent_bookings.append({
                    'id': booking.id,
                    'candidate_name': user.name or user.email,
                    'candidate_email': user.email,
                    'slot_date': slot.date.strftime('%b %d, %Y'),
                    'slot_time': f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}",
                    'status': 'confirmed' if booking.confirmed else 'cancelled',
                    'booked_at': booking.booked_at
                })
        
        # Today's interviews
        todays_slots = InterviewSlot.query.filter(
            InterviewSlot.date == today
        ).order_by(InterviewSlot.start_time).all()
        
        todays_interviews = []
        upcoming_interviews_count = 0
        for slot in todays_slots:
            bookings = SlotBooking.query.filter_by(slot_id=slot.id, confirmed=True).all()
            for booking in bookings:
                user = User.query.get(booking.user_id)
                if user:
                    todays_interviews.append({
                        'candidate_name': user.name or user.email,
                        'slot_time': f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}",
                        'status': 'confirmed' if booking.confirmed else 'cancelled'
                    })
                    upcoming_interviews_count += 1
        
        # Candidates who haven't booked slots yet
        candidates_without_slots = User.query.filter_by(role='candidate').outerjoin(
            SlotBooking, (SlotBooking.user_id == User.id) & (SlotBooking.confirmed == True)
        ).filter(SlotBooking.id == None).count()
        
        # Login statistics - candidates who never logged in (first_login still True)
        never_logged_in = User.query.filter_by(role='candidate', first_login=True).count()
    
        # Pending reviews (applications with 'pending' status)
        pending_reviews = Application.query.filter_by(status='pending').count()
        
        # Growth statistics
        candidates_last_week = User.query.filter(
            User.role == 'candidate',
            User.created_at < week_ago
        ).count()
        
        candidate_growth = 0
        if candidates_last_week > 0:
            candidate_growth = int(((total_candidates - candidates_last_week) / candidates_last_week) * 100)
        else:
            candidate_growth = 100 if total_candidates > 0 else 0
            
        growth_stats = {
            'candidates': candidate_growth
        }

        # For the template compatibility
        slots_filled = confirmed_bookings

        return render_template('admin/dashboard.html',
                             now=now,
                             today=today,
                             total_candidates=total_candidates,
                             active_candidates=active_candidates,
                             recent_candidates=recent_candidates,
                             total_slots=total_slots,
                             active_slots=active_slots,
                             total_bookings=total_bookings,
                             confirmed_bookings=confirmed_bookings,
                             cancelled_bookings=cancelled_bookings,
                             total_capacity=total_capacity,
                             total_booked=total_booked,
                             capacity_percentage=capacity_percentage,
                             dept_stats=dept_stats,
                             status_stats=status_stats,
                             upcoming_slots=upcoming_slots,
                             recent_bookings=recent_bookings,
                             todays_interviews=todays_interviews,
                             upcoming_interviews_count=upcoming_interviews_count,
                             candidates_without_slots=candidates_without_slots,
                             never_logged_in=never_logged_in,
                             slots_filled=slots_filled,
                             pending_reviews=pending_reviews,
                             growth_stats=growth_stats)
    except Exception as e:
        import traceback
        logger.error(f"Dashboard error: {str(e)}")
        logger.error(traceback.format_exc())
        # Return error details for debugging
        return f"<h1>Dashboard Error</h1><pre>{traceback.format_exc()}</pre>", 500


@admin_bp.route('/candidates')
@login_required
@admin_required
def candidates():
    """List all candidates with filters"""
    # Get filter parameters
    status = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    # Build query
    query = User.query.filter_by(role='candidate')
    
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    if status != 'all':
        query = query.join(Application).filter(Application.status == status)
    
    candidates = query.order_by(User.created_at.desc()).all()
    
    return render_template('admin/candidates.html', candidates=candidates, 
                         current_status=status, search=search)


@admin_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_candidates():
    """Upload candidates via Excel/CSV file"""
    if request.method == 'POST':
        # Check if file exists
        if 'excel_file' not in request.files:
            flash('No file uploaded', 'danger')
            return redirect(request.url)
        
        file = request.files['excel_file']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Invalid file format. Use .xlsx or .csv', 'danger')
            return redirect(request.url)
        
        # Parse file
        df, error = parse_excel_file(file)
        
        if error:
            flash(error, 'danger')
            return redirect(request.url)
        
        # Validate required columns
        required_cols = ['Name', 'Email', 'Department', 'Year']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            flash(f'Missing required columns: {", ".join(missing_cols)}', 'danger')
            return redirect(request.url)
        
        # Process each row
        success_count = 0
        error_count = 0
        errors = []
        created_credentials = []  # Store credentials to show to admin
        users_to_email = []  # Store users for batch email sending
        
        for idx, row in df.iterrows():
            # Validate row data
            is_valid, error_msg, cleaned_data = validate_candidate_data(row, idx + 2)
            
            if not is_valid:
                errors.append(error_msg)
                error_count += 1
                continue
            
            # Create candidate (without sending email yet)
            user, result = create_candidate(
                name=cleaned_data['name'],
                email=cleaned_data['email'],
                phone=cleaned_data['phone'],
                department=cleaned_data['department'],
                year=cleaned_data['year'],
                skills=cleaned_data['skills'],
                extra_fields=cleaned_data.get('extra_fields'),
                send_email=False  # Don't send email yet, we'll do batch send
            )
            
            if user:
                success_count += 1
                # Store credentials for display (result is the temp password)
                created_credentials.append({
                    'name': cleaned_data['name'],
                    'email': cleaned_data['email'],
                    'password': result
                })
                # Store for batch email
                users_to_email.append({
                    'user': user,
                    'temp_password': result
                })
            else:
                errors.append(f"Row {idx + 2}: {result}")
                error_count += 1
        
        # Send credentials emails and SMS to all successfully created users
        if users_to_email:
            from app.utils.email import send_credentials_email
            from app.utils.sms import send_credentials_sms
            email_success_count = 0
            sms_success_count = 0
            for item in users_to_email:
                try:
                    if send_credentials_email(item['user'], item['temp_password']):
                        email_success_count += 1
                    if send_credentials_sms(item['user'], item['temp_password']):
                        sms_success_count += 1
                except Exception as e:
                    current_app.logger.warning(f"Failed to send notification to {item['user'].email}: {str(e)}")
            
            current_app.logger.info(f"Sent credentials: {email_success_count} emails, {sms_success_count} SMS")
        
        # Show results
        if success_count > 0:
            flash(f'Successfully added {success_count} candidates', 'success')
            log_audit(current_user.id, 'BULK_UPLOAD', f'{success_count} candidates added, {error_count} errors')
        
        if error_count > 0:
            flash(f'{error_count} rows failed. See errors below.', 'warning')
            for error in errors[:10]:  # Show first 10 errors
                flash(error, 'danger')
        
        # Render results page with credentials
        if created_credentials:
            return render_template('admin/upload_results.html', credentials=created_credentials)
        
        # Fallback if no credentials were created
        return redirect(url_for('admin.candidates'))
        
        return redirect(url_for('admin.candidates'))
    
    return render_template('admin/upload.html')


@admin_bp.route('/slots')
@login_required
@admin_required
def manage_slots():
    """Manage interview slots"""
    # Get date filter
    date_filter = request.args.get('date', '')
    
    query = InterviewSlot.query
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=filter_date)
        except ValueError:
            pass
    
    slots = query.order_by(InterviewSlot.date, InterviewSlot.start_time).all()
    
    # Get today's date for the date picker min attribute
    today = datetime.now().date().isoformat()
    
    return render_template('admin/slots.html', slots=slots, date_filter=date_filter, today=today)


@admin_bp.route('/slots/create', methods=['POST'])
@login_required
@admin_required
def create_slot():
    """Create a new interview slot"""
    try:
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        capacity = int(request.form.get('capacity', 1))
        
        # Validate inputs
        if not all([date_str, start_time_str, end_time_str]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        # Parse date and time
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate date is not in the past
        today = datetime.now().date()
        if slot_date < today:
            flash('Cannot create slots for past dates', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        # Validate times
        if end_time <= start_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        # Check for conflicts
        conflicts = InterviewSlot.query.filter_by(date=slot_date).filter(
            db.or_(
                db.and_(InterviewSlot.start_time <= start_time, InterviewSlot.end_time > start_time),
                db.and_(InterviewSlot.start_time < end_time, InterviewSlot.end_time >= end_time)
            )
        ).first()
        
        if conflicts:
            flash('Time slot conflicts with existing slot', 'warning')
        
        # Create slot
        slot = InterviewSlot(
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            created_by=current_user.id
        )
        
        db.session.add(slot)
        db.session.commit()
        
        flash('Slot created successfully', 'success')
        log_audit(current_user.id, 'CREATE_SLOT', f'Created slot for {date_str} {start_time_str}-{end_time_str}')
    
    except ValueError as e:
        flash(f'Invalid date or time format: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Error creating slot: {str(e)}', 'danger')
        db.session.rollback()
    
    return redirect(url_for('admin.manage_slots'))


@admin_bp.route('/slots/create-bulk', methods=['POST'])
@login_required
@admin_required
def create_bulk_slots():
    """Create multiple interview slots automatically based on time intervals"""
    try:
        # Get form data
        dates_str = request.form.getlist('dates[]')  # Multiple dates
        start_time_str = request.form.get('bulk_start_time')
        end_time_str = request.form.get('bulk_end_time')
        interval_minutes = int(request.form.get('interval', 30))
        capacity = int(request.form.get('bulk_capacity', 1))
        
        # Validate inputs
        if not all([dates_str, start_time_str, end_time_str]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        if interval_minutes < 5 or interval_minutes > 480:
            flash('Interval must be between 5 and 480 minutes', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        # Parse times
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Validate times
        if end_time <= start_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        # Calculate total duration in minutes
        start_datetime = datetime.combine(datetime.today(), start_time)
        end_datetime = datetime.combine(datetime.today(), end_time)
        total_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        if total_minutes < interval_minutes:
            flash('Time range is too short for the specified interval', 'danger')
            return redirect(url_for('admin.manage_slots'))
        
        today = datetime.now().date()
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        # Process each date
        for date_str in dates_str:
            try:
                slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Skip past dates
                if slot_date < today:
                    skipped_count += 1
                    continue
                
                # Generate time slots based on interval
                current_time = start_time
                current_datetime = datetime.combine(datetime.today(), start_time)
                
                while current_datetime < end_datetime:
                    # Calculate slot end time
                    slot_end_datetime = current_datetime + timedelta(minutes=interval_minutes)
                    
                    # Don't exceed the overall end time
                    if slot_end_datetime > end_datetime:
                        break
                    
                    slot_start_time = current_datetime.time()
                    slot_end_time = slot_end_datetime.time()
                    
                    # Check for conflicts
                    conflicts = InterviewSlot.query.filter_by(date=slot_date).filter(
                        db.or_(
                            db.and_(InterviewSlot.start_time <= slot_start_time, InterviewSlot.end_time > slot_start_time),
                            db.and_(InterviewSlot.start_time < slot_end_time, InterviewSlot.end_time >= slot_end_time),
                            db.and_(InterviewSlot.start_time >= slot_start_time, InterviewSlot.end_time <= slot_end_time)
                        )
                    ).first()
                    
                    if not conflicts:
                        # Create slot
                        slot = InterviewSlot(
                            date=slot_date,
                            start_time=slot_start_time,
                            end_time=slot_end_time,
                            capacity=capacity,
                            created_by=current_user.id
                        )
                        db.session.add(slot)
                        created_count += 1
                    else:
                        skipped_count += 1
                    
                    # Move to next interval
                    current_datetime = slot_end_datetime
                
            except ValueError as e:
                error_count += 1
                logger.error(f"Error processing date {date_str}: {str(e)}")
        
        # Commit all slots
        db.session.commit()
        
        # Show results
        if created_count > 0:
            flash(f'Successfully created {created_count} slots', 'success')
            log_audit(current_user.id, 'CREATE_BULK_SLOTS', 
                     f'Created {created_count} slots with {interval_minutes}min intervals')
        
        if skipped_count > 0:
            flash(f'{skipped_count} slots were skipped (conflicts or past dates)', 'info')
        
        if error_count > 0:
            flash(f'{error_count} slots had errors', 'warning')
        
        if created_count == 0 and error_count == 0:
            flash('No slots were created. Check for conflicts or date issues.', 'warning')
    
    except ValueError as e:
        flash(f'Invalid input format: {str(e)}', 'danger')
        db.session.rollback()
    except Exception as e:
        flash(f'Error creating slots: {str(e)}', 'danger')
        logger.error(f"Bulk slot creation error: {str(e)}")
        db.session.rollback()
    
    return redirect(url_for('admin.manage_slots'))


@admin_bp.route('/slots/<int:slot_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_slot(slot_id):
    """Delete an interview slot"""
    slot = InterviewSlot.query.get_or_404(slot_id)
    
    # Check if slot has bookings
    if slot.current_bookings > 0:
        flash('Cannot delete slot with existing bookings', 'danger')
        return redirect(url_for('admin.manage_slots'))
    
    db.session.delete(slot)
    db.session.commit()
    
    flash('Slot deleted successfully', 'success')
    log_audit(current_user.id, 'DELETE_SLOT', f'Deleted slot {slot_id}')
    
    return redirect(url_for('admin.manage_slots'))


@admin_bp.route('/slots/<int:slot_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_slot(slot_id):
    """Toggle slot open/closed status"""
    slot = InterviewSlot.query.get_or_404(slot_id)
    
    slot.is_open = not slot.is_open
    db.session.commit()
    
    status = 'opened' if slot.is_open else 'closed'
    flash(f'Slot {status} successfully', 'success')
    log_audit(current_user.id, 'TOGGLE_SLOT', f'Slot {slot_id} {status}')
    
    return redirect(url_for('admin.manage_slots'))


@admin_bp.route('/announcements')
@login_required
@admin_required
def announcements():
    """Manage announcements"""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=announcements)


@admin_bp.route('/announcements/create', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    """Create a new announcement"""
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    
    if not title or not content:
        flash('Title and content are required', 'danger')
        return redirect(url_for('admin.announcements'))
    
    announcement = Announcement(
        title=title,
        content=content,
        created_by=current_user.id
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    # Send email and SMS to all candidates
    candidates = User.query.filter_by(role='candidate').all()
    if candidates:
        # Send emails
        success_count, failed_count = send_announcement_email(candidates, title, content)
        
        # Send SMS
        from app.utils.sms import send_announcement_sms
        sms_success = send_announcement_sms(candidates, title, content)
        
        if success_count > 0 or sms_success > 0:
            flash(f'Announcement sent: {success_count} emails, {sms_success} SMS', 'success')
        if failed_count > 0:
            flash(f'Failed to send email to {failed_count} candidate(s)', 'warning')
    else:
        flash('Announcement created successfully', 'success')
    
    log_audit(current_user.id, 'CREATE_ANNOUNCEMENT', f'Created announcement: {title}')
    
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/announcements/<int:announcement_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_announcement(announcement_id):
    """Toggle announcement active status"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    announcement.is_active = not announcement.is_active
    db.session.commit()
    
    status = 'activated' if announcement.is_active else 'deactivated'
    flash(f'Announcement {status} successfully', 'success')
    
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    """Delete an announcement"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    db.session.delete(announcement)
    db.session.commit()
    
    flash('Announcement deleted successfully', 'success')
    log_audit(current_user.id, 'DELETE_ANNOUNCEMENT', f'Deleted announcement {announcement_id}')
    
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/candidate/<int:user_id>')
@login_required
@admin_required
def view_candidate(user_id):
    """View candidate details"""
    user = User.query.get_or_404(user_id)
    
    if user.role != 'candidate':
        flash('Invalid candidate', 'danger')
        return redirect(url_for('admin.candidates'))
    
    return render_template('admin/candidate_detail.html', candidate=user)


@admin_bp.route('/candidate/<int:user_id>/status', methods=['POST'])
@login_required
@admin_required
def update_candidate_status(user_id):
    """Update candidate application status"""
    user = User.query.get_or_404(user_id)
    new_status = request.form.get('status')
    
    if user.application:
        user.application.status = new_status
        db.session.commit()
        
        flash(f'Status updated to {new_status}', 'success')
        log_audit(current_user.id, 'UPDATE_STATUS', f'Updated candidate {user_id} status to {new_status}')
    
    return redirect(url_for('admin.view_candidate', user_id=user_id))


@admin_bp.route('/candidate/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_candidate(user_id):
    """Edit candidate details"""
    from app.auth.utils import hash_password
    
    user = User.query.get_or_404(user_id)
    
    if user.role != 'candidate':
        flash('Invalid candidate', 'danger')
        return redirect(url_for('admin.candidates'))
    
    if request.method == 'POST':
        try:
            # Update basic info
            user.name = request.form.get('name')
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            
            # Update password if provided
            new_password = request.form.get('password')
            if new_password and new_password.strip():
                user.password_hash = hash_password(new_password)
                user.first_login = True  # Force password change on next login
            
            # Update application details if exists
            if user.application:
                user.application.department = request.form.get('department')
                user.application.year = request.form.get('year')
                user.application.skills = request.form.get('skills')
            
            db.session.commit()
            
            flash('Candidate updated successfully', 'success')
            log_audit(current_user.id, 'EDIT_CANDIDATE', f'Updated candidate {user_id}: {user.email}')
            
            return redirect(url_for('admin.view_candidate', user_id=user_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating candidate: {str(e)}', 'danger')
    
    return render_template('admin/edit_candidate.html', candidate=user)


@admin_bp.route('/candidate/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_candidate(user_id):
    """Delete a candidate"""
    user = User.query.get_or_404(user_id)
    
    if user.role != 'candidate':
        flash('Invalid candidate', 'danger')
        return redirect(url_for('admin.candidates'))
    
    try:
        candidate_email = user.email
        
        # Delete related records (cascade should handle this, but being explicit)
        if user.application:
            db.session.delete(user.application)
        
        # Delete slot bookings
        SlotBooking.query.filter_by(user_id=user_id).delete()
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Candidate {candidate_email} deleted successfully', 'success')
        log_audit(current_user.id, 'DELETE_CANDIDATE', f'Deleted candidate {user_id}: {candidate_email}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting candidate: {str(e)}', 'danger')
    
    return redirect(url_for('admin.candidates'))


@admin_bp.route('/bookings')
@login_required
@admin_required
def manage_bookings():
    """View all slot bookings with candidate details"""
    # Get filter parameters
    date_filter = request.args.get('date', '')
    status_filter = request.args.get('status', 'all')
    
    query = SlotBooking.query.join(
        User, SlotBooking.user_id == User.id
    ).join(
        InterviewSlot, SlotBooking.slot_id == InterviewSlot.id
    ).join(
        Application, User.id == Application.user_id, isouter=True
    )
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(InterviewSlot.date == filter_date)
        except ValueError:
            pass
    
    if status_filter != 'all':
        query = query.filter(Application.status == status_filter)
    
    bookings = query.order_by(InterviewSlot.date, InterviewSlot.start_time).all()
    
    # Get unique dates for filter dropdown
    booking_dates = db.session.query(InterviewSlot.date).join(SlotBooking).distinct().order_by(InterviewSlot.date).all()
    
    return render_template('admin/bookings.html', 
                         bookings=bookings,
                         booking_dates=booking_dates,
                         date_filter=date_filter,
                         status_filter=status_filter)


@admin_bp.route('/export/candidates')
@login_required
@admin_required
def export_candidates():
    """Export all candidates data to Excel"""
    # Query all candidates with their details
    candidates = User.query.filter_by(role='candidate').all()
    
    # Collect all unique extra field keys across all candidates
    all_extra_fields = set()
    for candidate in candidates:
        if candidate.application and candidate.application.extra_fields:
            all_extra_fields.update(candidate.application.extra_fields.keys())
    
    all_extra_fields = sorted(all_extra_fields)  # Sort for consistent column order
    
    data = []
    for candidate in candidates:
        booking = SlotBooking.query.filter_by(user_id=candidate.id).first()
        slot = booking.slot if booking else None
        
        row = {
            'Name': candidate.name,
            'Email': candidate.email,
            'Phone': candidate.phone or '',
            'Department': candidate.application.department if candidate.application else '',
            'Year': candidate.application.year if candidate.application else '',
            'Skills': candidate.application.skills if candidate.application else '',
        }
        
        # Add extra fields dynamically
        if candidate.application and candidate.application.extra_fields:
            for field in all_extra_fields:
                row[field] = candidate.application.extra_fields.get(field, '')
        else:
            for field in all_extra_fields:
                row[field] = ''
        
        # Add status and slot information
        row.update({
            'Status': candidate.application.status if candidate.application else '',
            'Slot Date': slot.date.strftime('%Y-%m-%d') if slot else 'Not Booked',
            'Slot Time': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}" if slot else '',
            'Booking Date': booking.booked_at.strftime('%Y-%m-%d %H:%M') if booking else '',
            'First Login Done': 'No' if candidate.first_login else 'Yes',
            'Account Active': 'Yes' if candidate.is_active else 'No',
            'Registered On': candidate.created_at.strftime('%Y-%m-%d %H:%M')
        })
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Candidates', index=False)
    output.seek(0)
    
    filename = f'candidates_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    log_audit(current_user.id, 'EXPORT_CANDIDATES', f'Exported {len(candidates)} candidates to Excel')
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@admin_bp.route('/export/bookings')
@login_required
@admin_required
def export_bookings():
    """Export all bookings data to Excel"""
    bookings = SlotBooking.query.join(
        User, SlotBooking.user_id == User.id
    ).join(
        InterviewSlot, SlotBooking.slot_id == InterviewSlot.id
    ).order_by(
        InterviewSlot.date, InterviewSlot.start_time
    ).all()
    
    data = []
    for booking in bookings:
        data.append({
            'Candidate Name': booking.user.name,
            'Email': booking.user.email,
            'Phone': booking.user.phone or '',
            'Department': booking.user.application.department if booking.user.application else '',
            'Year': booking.user.application.year if booking.user.application else '',
            'Interview Date': booking.slot.date.strftime('%Y-%m-%d'),
            'Day': booking.slot.date.strftime('%A'),
            'Start Time': booking.slot.start_time.strftime('%H:%M'),
            'End Time': booking.slot.end_time.strftime('%H:%M'),
            'Booking Confirmed': 'Yes' if booking.confirmed else 'No',
            'Booked At': booking.booked_at.strftime('%Y-%m-%d %H:%M'),
            'Status': booking.user.application.status if booking.user.application else ''
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Bookings', index=False)
    output.seek(0)
    
    filename = f'bookings_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    log_audit(current_user.id, 'EXPORT_BOOKINGS', f'Exported {len(bookings)} bookings to Excel')
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@admin_bp.route('/export/full-report')
@login_required
@admin_required
def export_full_report():
    """Export comprehensive report with multiple sheets"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: All Candidates (with extra fields)
        candidates = User.query.filter_by(role='candidate').all()
        
        # Collect all unique extra field keys
        all_extra_fields = set()
        for c in candidates:
            if c.application and c.application.extra_fields:
                all_extra_fields.update(c.application.extra_fields.keys())
        all_extra_fields = sorted(all_extra_fields)
        
        candidates_data = []
        for c in candidates:
            booking = SlotBooking.query.filter_by(user_id=c.id).first()
            slot = booking.slot if booking else None
            
            row = {
                'Name': c.name,
                'Email': c.email,
                'Phone': c.phone or '',
                'Department': c.application.department if c.application else '',
                'Year': c.application.year if c.application else '',
                'Skills': c.application.skills if c.application else '',
            }
            
            # Add extra fields dynamically
            if c.application and c.application.extra_fields:
                for field in all_extra_fields:
                    row[field] = c.application.extra_fields.get(field, '')
            else:
                for field in all_extra_fields:
                    row[field] = ''
            
            row.update({
                'Status': c.application.status if c.application else '',
                'Slot Date': slot.date.strftime('%Y-%m-%d') if slot else 'Not Booked',
                'Slot Time': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}" if slot else '',
                'First Login Done': 'No' if c.first_login else 'Yes',
                'Registered On': c.created_at.strftime('%Y-%m-%d %H:%M')
            })
            
            candidates_data.append(row)
        pd.DataFrame(candidates_data).to_excel(writer, sheet_name='All Candidates', index=False)
        
        # Sheet 2: Interview Schedule (by date)
        slots = InterviewSlot.query.order_by(InterviewSlot.date, InterviewSlot.start_time).all()
        schedule_data = []
        for slot in slots:
            for booking in slot.bookings:
                schedule_data.append({
                    'Date': slot.date.strftime('%Y-%m-%d'),
                    'Day': slot.date.strftime('%A'),
                    'Time': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}",
                    'Candidate Name': booking.user.name,
                    'Email': booking.user.email,
                    'Phone': booking.user.phone or '',
                    'Department': booking.user.application.department if booking.user.application else '',
                    'Status': booking.user.application.status if booking.user.application else ''
                })
        pd.DataFrame(schedule_data).to_excel(writer, sheet_name='Interview Schedule', index=False)
        
        # Sheet 3: Slot Summary
        slot_summary = []
        for slot in slots:
            slot_summary.append({
                'Date': slot.date.strftime('%Y-%m-%d'),
                'Day': slot.date.strftime('%A'),
                'Start Time': slot.start_time.strftime('%H:%M'),
                'End Time': slot.end_time.strftime('%H:%M'),
                'Capacity': slot.capacity,
                'Booked': slot.current_bookings,
                'Available': slot.available_spots,
                'Status': 'Open' if slot.is_open else 'Closed',
                'Full': 'Yes' if slot.is_full else 'No'
            })
        pd.DataFrame(slot_summary).to_excel(writer, sheet_name='Slot Summary', index=False)
        
        # Sheet 4: Department-wise Summary
        dept_stats = db.session.query(
            Application.department,
            func.count(Application.id).label('total'),
            func.sum(db.case((Application.status == 'selected', 1), else_=0)).label('selected'),
            func.sum(db.case((Application.status == 'rejected', 1), else_=0)).label('rejected'),
            func.sum(db.case((Application.status == 'interviewed', 1), else_=0)).label('interviewed'),
            func.sum(db.case((Application.status == 'slot_selected', 1), else_=0)).label('slot_selected'),
            func.sum(db.case((Application.status == 'pending', 1), else_=0)).label('pending')
        ).group_by(Application.department).all()
        
        dept_data = []
        for dept in dept_stats:
            dept_data.append({
                'Department': dept.department or 'Unknown',
                'Total Candidates': dept.total,
                'Selected': dept.selected or 0,
                'Rejected': dept.rejected or 0,
                'Interviewed': dept.interviewed or 0,
                'Slot Selected': dept.slot_selected or 0,
                'Pending': dept.pending or 0
            })
        pd.DataFrame(dept_data).to_excel(writer, sheet_name='Department Summary', index=False)
        
        # Sheet 5: Status-wise List
        for status in ['selected', 'rejected', 'interviewed', 'slot_selected', 'pending']:
            apps = Application.query.filter_by(status=status).all()
            status_data = []
            for app in apps:
                booking = SlotBooking.query.filter_by(user_id=app.user_id).first()
                slot = booking.slot if booking else None
                status_data.append({
                    'Name': app.user.name,
                    'Email': app.user.email,
                    'Phone': app.user.phone or '',
                    'Department': app.department,
                    'Year': app.year,
                    'Interview Date': slot.date.strftime('%Y-%m-%d') if slot else 'N/A',
                    'Interview Time': f"{slot.start_time.strftime('%H:%M')}" if slot else 'N/A'
                })
            sheet_name = status.replace('_', ' ').title()
            pd.DataFrame(status_data).to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    
    filename = f'full_recruitment_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    log_audit(current_user.id, 'EXPORT_FULL_REPORT', 'Exported comprehensive recruitment report')
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@admin_bp.route('/slots/<int:slot_id>/bookings')
@login_required
@admin_required
def view_slot_bookings(slot_id):
    """View all bookings for a specific slot"""
    slot = InterviewSlot.query.get_or_404(slot_id)
    bookings = SlotBooking.query.filter_by(slot_id=slot_id).join(User).all()
    
    return render_template('admin/slot_bookings.html', slot=slot, bookings=bookings)


@admin_bp.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
@admin_required
def admin_cancel_booking(booking_id):
    """Admin can cancel any booking"""
    booking = SlotBooking.query.get_or_404(booking_id)
    
    try:
        slot = InterviewSlot.query.with_for_update().get(booking.slot_id)
        user = booking.user
        
        # Decrement slot counter
        slot.current_bookings = max(0, slot.current_bookings - 1)
        
        # Update application status
        if user.application:
            user.application.status = 'pending'
        
        db.session.delete(booking)
        db.session.commit()
        
        flash(f'Booking cancelled for {user.name}', 'success')
        log_audit(current_user.id, 'ADMIN_CANCEL_BOOKING', f'Cancelled booking for {user.email}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling booking: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('admin.manage_bookings'))


# ============================================
# ADMIN MANAGEMENT (Super Admin Only)
# ============================================

@admin_bp.route('/admins')
@login_required
@super_admin_required
def manage_admins():
    """View and manage admin users (super admin only)"""
    admins = User.query.filter_by(role='admin').order_by(User.created_at.desc()).all()
    return render_template('admin/manage_admins.html', admins=admins)


@admin_bp.route('/admins/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_admin():
    """Create a new admin user (super admin only)"""
    from app.utils.security import hash_password, generate_random_password
    from app.utils.email import send_admin_credentials_email
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        send_email = request.form.get('send_email') == 'on'
        
        # Validation
        if not name or not email:
            flash('Name and email are required.', 'danger')
            return render_template('admin/create_admin.html')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('admin/create_admin.html')
        
        try:
            # Generate temporary password
            temp_password = generate_random_password()
            
            # Create admin user
            new_admin = User(
                name=name,
                email=email,
                phone=phone,
                password_hash=hash_password(temp_password),
                role='admin',
                is_super_admin=False,  # Regular admin, not super admin
                is_active=True,
                first_login=True,  # Must change password on first login
                created_by=current_user.id
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            # Send credentials via email and SMS if requested
            if send_email:
                send_admin_credentials_email(new_admin, temp_password)
                
                # Also send SMS
                from app.utils.sms import send_admin_credentials_sms
                send_admin_credentials_sms(new_admin, temp_password)
                
                flash(f'Admin "{name}" created. Credentials sent via email and SMS.', 'success')
            else:
                flash(f'Admin "{name}" created. Temporary password: {temp_password}', 'success')
            
            log_audit(current_user.id, 'CREATE_ADMIN', f'Created admin user: {email}')
            
            return redirect(url_for('admin.manage_admins'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating admin: {str(e)}")
            flash(f'Error creating admin: {str(e)}', 'danger')
    
    return render_template('admin/create_admin.html')


@admin_bp.route('/admins/<int:admin_id>/toggle', methods=['POST'])
@login_required
@super_admin_required
def toggle_admin_status(admin_id):
    """Activate/Deactivate an admin user (super admin only)"""
    admin = User.query.get_or_404(admin_id)
    
    # Cannot deactivate super admin
    if admin.check_is_super_admin:
        flash('Cannot deactivate the super admin.', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Cannot modify self
    if admin.id == current_user.id:
        flash('Cannot modify your own account.', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    admin.is_active = not admin.is_active
    db.session.commit()
    
    status = 'activated' if admin.is_active else 'deactivated'
    flash(f'Admin "{admin.name}" has been {status}.', 'success')
    log_audit(current_user.id, 'TOGGLE_ADMIN', f'{status.capitalize()} admin: {admin.email}')
    
    return redirect(url_for('admin.manage_admins'))


@admin_bp.route('/admins/<int:admin_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete_admin(admin_id):
    """Delete an admin user (super admin only)"""
    admin = User.query.get_or_404(admin_id)
    
    # Cannot delete super admin
    if admin.check_is_super_admin:
        flash('Cannot delete the super admin.', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    # Cannot delete self
    if admin.id == current_user.id:
        flash('Cannot delete your own account.', 'danger')
        return redirect(url_for('admin.manage_admins'))
    
    email = admin.email
    name = admin.name
    
    try:
        db.session.delete(admin)
        db.session.commit()
        flash(f'Admin "{name}" has been deleted.', 'success')
        log_audit(current_user.id, 'DELETE_ADMIN', f'Deleted admin: {email}')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting admin: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_admins'))
