from flask import Blueprint, render_template, request, flash, redirect, url_for, g, jsonify
from app.utils.decorators import auth_required
from app.services.assignment_service import (
    get_user_assignments, create_assignment, update_user_availability,
    get_project_assignments, get_role_assignments, get_all_users, get_all_roles
)
from datetime import datetime
import logging
from flask_wtf import FlaskForm
from flask_login import login_required

assignments_bp = Blueprint('assignments', __name__, url_prefix='/assignments')
logger = logging.getLogger(__name__)

@assignments_bp.route('/user/<username>')
@auth_required(['admin', 'manager'])
def user_assignments(username):
    """Przypisania użytkownika do projektów."""
    month_year = request.args.get('month_year', datetime.now().strftime('%Y-%m'))
    assignments = get_user_assignments(username, month_year)
    return render_template('assignments/user.html', 
                         assignments=assignments, 
                         username=username,
                         month_year=month_year)

@assignments_bp.route('/project/<project_key>')
@auth_required(['admin', 'manager'])
def project_assignments(project_key):
    """Przypisania do projektu."""
    month_year = request.args.get('month_year', datetime.now().strftime('%Y-%m'))
    assignments = get_project_assignments(project_key, month_year)
    
    # Oblicz sumy dla podsumowania
    total_planned_hours = sum(a['planned_hours'] for a in assignments)
    total_actual_hours = sum((a['actual_hours'] or 0) / 3600 for a in assignments)
    
    # Pobierz dostępnych użytkowników i role
    available_users = get_all_users()
    available_roles = get_all_roles()
    
    return render_template('assignments/project.html', 
                         assignments=assignments,
                         project_key=project_key,
                         month_year=month_year,
                         total_planned_hours=total_planned_hours,
                         total_actual_hours=total_actual_hours,
                         available_users=available_users,
                         available_roles=available_roles,
                         form=FlaskForm())  # Dla CSRF tokena

@assignments_bp.route('/create', methods=['POST'])
@auth_required(['admin'])
def create():
    """Utwórz nowe przypisanie."""
    try:
        assignment_data = {
            'user_name': request.form.get('user_name'),
            'project_key': request.form.get('project_key'),
            'role_id': request.form.get('role_id'),
            'planned_hours': float(request.form.get('planned_hours')),
            'month_year': request.form.get('month_year'),
            'assigned_by': g.user['username']
        }
        
        if create_assignment(assignment_data):
            flash('Przypisanie zostało utworzone.', 'success')
        else:
            flash('Wystąpił błąd podczas tworzenia przypisania.', 'danger')
            
        return redirect(request.referrer)
    except Exception as e:
        logger.error(f"Error creating assignment: {str(e)}")
        flash('Wystąpił błąd podczas tworzenia przypisania.', 'danger')
        return redirect(request.referrer)

@assignments_bp.route('/availability/update', methods=['POST'])
@auth_required(['admin', 'manager'])
def update_availability():
    """Aktualizuj dostępność użytkownika."""
    try:
        availability_data = {
            'working_days': int(request.form.get('working_days')),
            'holidays': int(request.form.get('holidays')),
            'leave_days': int(request.form.get('leave_days'))
        }
        
        username = request.form.get('username')
        month_year = request.form.get('month_year')
        
        if update_user_availability(username, month_year, availability_data):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Nie można zaktualizować dostępności'})
    except Exception as e:
        logger.error(f"Error updating availability: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@assignments_bp.route('/view')
@login_required
def view():
    """View my assignments."""
    return render_template('assignments/view.html')

@assignments_bp.route('/manage')
@login_required
def manage():
    """Manage team assignments."""
    return render_template('assignments/manage.html')

# Dodatkowe endpointy dla zarządzania przypisaniami... 