from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.utils.decorators import admin_required, auth_required
from app.models import User, Team, Leave
from app.services.leave_service import (
    get_user_leaves,
    create_leave_request,
    update_leave_status,
    delete_leave_request,
    get_team_leaves,
    create_leave,
    update_leave,
    delete_leave,
    approve_leave
)
from app.forms import LeaveForm
import logging
from app.models.holiday import Holiday
from app.extensions import db
from app.utils.auth import requires_auth, requires_admin
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from app.models.leave_balance import LeaveBalance
from app.utils.email import (
    send_leave_request_notification,
    send_leave_status_notification,
    send_team_leave_notification
)

leaves_bp = Blueprint('leaves', __name__, url_prefix='/leaves')
logger = logging.getLogger(__name__)

@leaves_bp.route('/')
@auth_required()
def index():
    """Show user's leaves."""
    leaves = get_user_leaves(current_user.id)
    return render_template('leaves/index.html', leaves=leaves)

@leaves_bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_leave():
    """Formularz wniosku urlopowego."""
    form = LeaveForm()
    if form.validate_on_submit():
        leave_data = {
            'user_id': current_user.id,
            'start_date': form.start_date.data,
            'end_date': form.end_date.data,
            'leave_type': form.leave_type.data,
            'description': form.description.data
        }
        
        if create_leave_request(leave_data):
            flash('Wniosek urlopowy został złożony.', 'success')
            return redirect(url_for('leaves.index'))
        flash('Wystąpił błąd podczas składania wniosku.', 'danger')
    
    return render_template('leaves/request.html', form=form)

@leaves_bp.route('/<int:leave_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_leave(leave_id):
    """Zatwierdzanie wniosku urlopowego."""
    if update_leave_status(leave_id, 'approved', current_user.id):
        flash('Wniosek został zatwierdzony.', 'success')
    else:
        flash('Wystąpił błąd podczas zatwierdzania wniosku.', 'danger')
    return redirect(url_for('leaves.index'))

@leaves_bp.route('/<int:leave_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_leave(leave_id):
    """Odrzucanie wniosku urlopowego."""
    if update_leave_status(leave_id, 'rejected', current_user.id):
        flash('Wniosek został odrzucony.', 'success')
    else:
        flash('Wystąpił błąd podczas odrzucania wniosku.', 'danger')
    return redirect(url_for('leaves.index'))

@leaves_bp.route('/<int:leave_id>/delete', methods=['POST'])
@login_required
def delete_leave(leave_id):
    """Usuwanie wniosku urlopowego."""
    leave = Leave.query.get_or_404(leave_id)
    
    if not current_user.is_admin and current_user.id != leave.user_id:
        flash('Nie masz uprawnień do usunięcia tego wniosku.', 'danger')
        return redirect(url_for('leaves.index'))
        
    if delete_leave_request(leave_id):
        flash('Wniosek został usunięty.', 'success')
    else:
        flash('Wystąpił błąd podczas usuwania wniosku.', 'danger')
    return redirect(url_for('leaves.index'))

@leaves_bp.route('/team/<int:team_id>')
@login_required
@admin_required
def team_leaves(team_id):
    """Lista urlopów zespołu."""
    team = Team.query.get_or_404(team_id)
    leaves = get_team_leaves(team_id)
    return render_template('leaves/team.html', team=team, leaves=leaves)

@leaves_bp.route('/calendar')
@login_required
def calendar():
    """Team leave calendar view."""
    try:
        # Get user's team members
        team_members = []
        if current_user.team:
            team_members = current_user.team.members
        else:
            # If user is not in a team, show all users
            team_members = User.query.filter_by(is_active=True).all()
        
        # Get available leave types
        leave_types = ['annual', 'sick', 'personal', 'other']
        
        # Get all leaves for the team members
        leaves = []
        if team_members:
            member_ids = [member.id for member in team_members]
            leaves = Leave.query.filter(Leave.user_id.in_(member_ids)).all()
        
        # Create leave form for the modal
        form = LeaveForm()
        
        return render_template(
            'leaves/calendar.html',
            team_members=team_members,
            leave_types=leave_types,
            leaves=leaves,
            form=form
        )
    except Exception as e:
        logger.error(f"Error loading team calendar: {str(e)}")
        flash('Error loading team calendar.', 'danger')
        return redirect(url_for('leaves.index'))

@leaves_bp.route('/api/team-leaves')
@requires_auth
def get_team_leaves():
    """Get leaves for team calendar."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        team_id = request.args.get('team_id', type=int)
        
        query = Leave.query
        
        if start_date:
            query = query.filter(Leave.start_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Leave.end_date <= datetime.strptime(end_date, '%Y-%m-%d'))
            
        # Filter by team if specified
        if team_id:
            team = Team.query.get_or_404(team_id)
            team_member_ids = [member.id for member in team.members]
            query = query.filter(Leave.user_id.in_(team_member_ids))
            
        leaves = query.order_by(Leave.start_date).all()
        
        return jsonify({
            'status': 'success',
            'data': [leave.to_dict() for leave in leaves]
        }), 200
    except Exception as e:
        logger.error(f"Error getting team leaves: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/leaves', methods=['GET'])
@requires_auth
def get_leaves():
    """Get all leaves with optional filtering."""
    try:
        user_id = request.args.get('user_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status')
        
        query = Leave.query
        
        if user_id:
            query = query.filter(Leave.user_id == user_id)
        if start_date:
            query = query.filter(Leave.start_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Leave.end_date <= datetime.strptime(end_date, '%Y-%m-%d'))
        if status:
            query = query.filter(Leave.status == status)
            
        leaves = query.order_by(Leave.start_date.desc()).all()
        
        return jsonify({
            'status': 'success',
            'data': [leave.to_dict() for leave in leaves]
        }), 200
    except Exception as e:
        logger.error(f"Error getting leaves: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/leaves', methods=['POST'])
@requires_auth
def create_leave():
    """Create a new leave request."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'start_date', 'end_date', 'leave_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
                
        # Convert date strings to datetime objects
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        
        # Calculate working days
        working_days = Holiday.get_working_days(start_date, end_date)
        
        # Check leave balance
        balance = LeaveBalance.get_or_create(data['user_id'])
        if not balance.can_request_leave(working_days):
            return jsonify({
                'status': 'error',
                'message': 'Insufficient leave balance'
            }), 400
        
        # Create new leave request
        leave = Leave(
            user_id=data['user_id'],
            start_date=start_date,
            end_date=end_date,
            leave_type=data['leave_type'],
            description=data.get('description'),
            duration=working_days
        )
        
        db.session.add(leave)
        
        # Update leave balance
        balance.update_balance(working_days, is_pending=True)
        
        db.session.commit()
        
        # Send notifications
        approvers = User.get_approvers()
        if approvers:
            send_leave_request_notification(leave.to_dict(), [a.email for a in approvers])
        
        return jsonify({
            'status': 'success',
            'message': 'Leave request created successfully',
            'data': leave.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating leave request: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/leaves/<int:leave_id>', methods=['PUT'])
@requires_auth
def update_leave(leave_id: int):
    """Update a leave request."""
    try:
        leave = Leave.query.get_or_404(leave_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'start_date' in data:
            leave.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        if 'end_date' in data:
            leave.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        if 'leave_type' in data:
            leave.leave_type = data['leave_type']
        if 'description' in data:
            leave.description = data['description']
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Leave request updated successfully',
            'data': leave.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating leave request: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/leaves/<int:leave_id>/approve', methods=['POST'])
@requires_admin
def api_approve_leave(leave_id: int):
    """Approve a leave request."""
    try:
        leave = Leave.query.get_or_404(leave_id)
        data = request.get_json()
        
        # Get leave balance
        balance = LeaveBalance.get_or_create(leave.user_id)
        
        # Update leave status
        leave.approve(data.get('approver_id'))
        
        # Update leave balance
        balance.update_balance(leave.duration, is_pending=False)
        
        db.session.commit()
        
        # Send notifications
        send_leave_status_notification(leave.to_dict(), leave.user.email)
        
        # Notify team members
        if leave.user.team:
            team_emails = [m.email for m in leave.user.team.members if m.id != leave.user_id]
            if team_emails:
                send_team_leave_notification(team_emails, leave.to_dict())
        
        return jsonify({
            'status': 'success',
            'message': 'Leave request approved successfully',
            'data': leave.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving leave request: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/leaves/<int:leave_id>/reject', methods=['POST'])
@requires_admin
def api_reject_leave(leave_id: int):
    """Reject a leave request."""
    try:
        leave = Leave.query.get_or_404(leave_id)
        data = request.get_json()
        
        # Get leave balance
        balance = LeaveBalance.get_or_create(leave.user_id)
        
        # Update leave status
        leave.reject(data.get('approver_id'))
        
        # Update leave balance (remove pending days)
        balance.update_balance(-leave.duration, is_pending=True)
        
        db.session.commit()
        
        # Send notification
        send_leave_status_notification(leave.to_dict(), leave.user.email)
        
        return jsonify({
            'status': 'success',
            'message': 'Leave request rejected successfully',
            'data': leave.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting leave request: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/leave-balances', methods=['GET'])
@requires_auth
def get_leave_balances():
    """Get leave balances for a user."""
    try:
        user_id = request.args.get('user_id', type=int)
        year = request.args.get('year', datetime.utcnow().year, type=int)
        
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'User ID is required'
            }), 400
            
        balance = LeaveBalance.get_or_create(user_id, year)
        
        return jsonify({
            'status': 'success',
            'data': balance.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error getting leave balances: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Holiday Management Routes

@leaves_bp.route('/api/holidays', methods=['GET'])
@requires_auth
def get_holidays():
    """Get all holidays with optional filtering."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        country_code = request.args.get('country_code', 'PL')
        
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            holidays = Holiday.get_holidays_in_range(start, end, country_code)
        else:
            holidays = Holiday.query.filter_by(country_code=country_code).all()
            
        return jsonify({
            'status': 'success',
            'data': [holiday.to_dict() for holiday in holidays]
        }), 200
    except Exception as e:
        logger.error(f"Error getting holidays: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/holidays', methods=['POST'])
@requires_admin
def create_holiday():
    """Create a new holiday."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['date', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
                
        # Create new holiday
        holiday = Holiday(
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            name=data['name'],
            description=data.get('description'),
            is_full_day=data.get('is_full_day', True),
            country_code=data.get('country_code', 'PL'),
            region=data.get('region'),
            type=data.get('type', 'public'),
            is_recurring=data.get('is_recurring', False),
            created_by_id=data.get('created_by_id')
        )
        
        db.session.add(holiday)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Holiday created successfully',
            'data': holiday.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating holiday: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/holidays/import', methods=['POST'])
@requires_admin
def import_holidays():
    """Import holidays from CSV file."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
            
        if not file.filename.endswith('.csv'):
            return jsonify({
                'status': 'error',
                'message': 'File must be a CSV'
            }), 400
            
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Import holidays from CSV
            created_by_id = request.form.get('created_by_id', type=int)
            results = Holiday.import_holidays_from_csv(filepath, created_by_id)
            
            return jsonify({
                'status': 'success',
                'message': 'Holidays imported successfully',
                'data': results
            }), 200
        finally:
            # Clean up temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
                
    except Exception as e:
        logger.error(f"Error importing holidays: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@leaves_bp.route('/api/holidays/working-days', methods=['GET'])
@requires_auth
def get_working_days():
    """Get number of working days between two dates."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        country_code = request.args.get('country_code', 'PL')
        
        if not start_date or not end_date:
            return jsonify({
                'status': 'error',
                'message': 'Start date and end date are required'
            }), 400
            
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        working_days = Holiday.get_working_days(start, end, country_code)
        
        return jsonify({
            'status': 'success',
            'data': {
                'working_days': working_days,
                'start_date': start_date,
                'end_date': end_date,
                'country_code': country_code
            }
        }), 200
    except Exception as e:
        logger.error(f"Error calculating working days: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 