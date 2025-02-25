from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
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

leaves_bp = Blueprint('leaves', __name__, url_prefix='/leaves')
logger = logging.getLogger(__name__)

@leaves_bp.route('/')
@auth_required()
def my_leaves():
    """Show user's leaves."""
    return render_template('leaves/index.html')

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
    """Kalendarz urlopów."""
    return render_template('leaves/calendar.html')

@leaves_bp.route('/api/leaves')
@login_required
def get_leaves():
    """API do pobierania urlopów."""
    leaves = Leave.query.all()
    return jsonify([leave.to_dict() for leave in leaves]) 