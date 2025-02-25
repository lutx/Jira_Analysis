from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for, send_from_directory, session
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.utils.db import get_db
from app.services import hash_password
from app.services.jira_service import get_jira_service, sync_jira_users, sync_jira_data, test_connection, save_jira_config, get_jira_projects, JiraService
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.team import Team
from app.models.portfolio import Portfolio
from app.models.project import Project
from app.extensions import db, cache, csrf
from flask_wtf.csrf import generate_csrf
from app.forms.admin import UserForm, RoleForm, JiraSettingsForm, SystemSettingsForm, SettingsForm
from app.forms.team import TeamForm
from app.forms.portfolio import PortfolioForm
from app.forms.project import ProjectForm
from app.models.jira_config import JiraConfig
from app.utils.crypto import encrypt_password
from app.services.admin_service import save_app_settings
from app.exceptions import JiraValidationError, JiraConnectionError
import logging
from datetime import datetime, timezone, timedelta
import os
import json
import csv
import io
from typing import Dict, Any
from app.models.worklog import Worklog
from app.services.jira_client import get_jira_client
from app.models.issue import Issue
from jira import JIRA
import base64
import requests
from pathlib import Path
from app.models.leave_request import LeaveRequest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import traceback

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

# Remove CSRF exemption
# csrf.exempt(admin_bp)

@admin_bp.after_request
def after_request(response):
    """Add CSRF token to response headers."""
    response.headers.set('X-CSRF-Token', generate_csrf())
    return response

@admin_bp.context_processor
def inject_admin_context():
    """Dodaje wspólne dane dla wszystkich widoków admina."""
    return {
        'notifications_count': get_notifications_count(),
        'active_menu': request.endpoint
    }

def get_notifications_count():
    """Pobiera liczbę nieprzeczytanych powiadomień."""
    # Tu dodaj logikę liczenia powiadomień
    return 0

def get_admin_stats():
    """Get admin dashboard statistics."""
    try:
        from app.services.jira_service import get_jira_service
        from sqlalchemy import text
        
        jira_service = get_jira_service()
        jira_connected = False
        
        if jira_service and jira_service.is_connected:
            jira_connected = True
            logger.info("JIRA service is connected")
        else:
            logger.warning("JIRA service is not connected")
            
        # Use raw SQL to count teams to avoid SQLAlchemy model mapping issues
        teams_count = db.session.execute(text("SELECT COUNT(*) FROM teams")).scalar()
            
        return {
            'users_count': User.query.count(),
            'teams_count': teams_count,
            'projects_count': Project.query.count(),
            'jira_connected': jira_connected
        }
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}", exc_info=True)
        return {
            'users_count': 0,
            'teams_count': 0,
            'projects_count': 0,
            'jira_connected': False
        }

@admin_bp.context_processor
def inject_admin_stats():
    """Inject common stats into all admin templates."""
    return {'stats': get_admin_stats()}

@admin_bp.before_request
@login_required
def before_request():
    """Sprawdź uprawnienia przed każdym requestem."""
    if not current_user.is_admin:
        flash('Brak uprawnień do tej sekcji.', 'danger')
        return redirect(url_for('main.dashboard'))

@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin panel home page."""
    return render_template('admin/index.html')

# Add alias route for home
admin_bp.add_url_rule('/', endpoint='home', view_func=index)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """User management page."""
    try:
        # Use joinedload to efficiently load users with their roles in a single query
        users = User.query.options(
            db.joinedload(User.roles),
            db.joinedload(User.user_roles)
        ).all()
        all_roles = Role.query.all()
        form = UserForm()
        return render_template('admin/users/index.html', users=users, form=form, all_roles=all_roles)
    except Exception as e:
        logger.error(f"Error in manage_users view: {str(e)}")
        flash('Error loading users', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/roles', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_roles():
    """Role management page."""
    try:
        form = RoleForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                try:
                    role = Role(
                        name=form.name.data,
                        description=form.description.data
                    )
                    role.set_permissions(form.permissions.data)
                    db.session.add(role)
                    db.session.commit()
                    flash('Role created successfully.', 'success')
                    return redirect(url_for('admin.manage_roles'))
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.error(f"Database error creating role: {str(e)}", exc_info=True)
                    flash('Database error occurred while creating role.', 'danger')
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error creating role: {str(e)}", exc_info=True)
                    flash('An error occurred while creating role.', 'danger')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{getattr(form, field).label.text}: {error}', 'danger')

        roles = Role.query.all()
        return render_template('admin/roles.html', roles=roles, form=form)
    except Exception as e:
        logger.error(f"Error in manage_roles view: {str(e)}", exc_info=True)
        flash('An error occurred while managing roles.', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/roles/<int:role_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_role(role_id):
    """Manage specific role."""
    try:
        role = Role.query.get_or_404(role_id)
        
        if request.method == 'GET':
            return jsonify(role.to_dict())
            
        elif request.method == 'PUT':
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400
                
            role.name = data.get('name', role.name)
            role.description = data.get('description', role.description)
            if 'permissions' in data:
                role.set_permissions(data['permissions'])
                
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Role updated successfully'})
            
        elif request.method == 'DELETE':
            if role.name in ['superadmin', 'admin', 'user']:
                return jsonify({'status': 'error', 'message': 'Cannot delete system roles'}), 400
                
            db.session.delete(role)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Role deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing role {role_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/teams', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_teams():
    """Team management page."""
    try:
        # Initialize form first to catch any form-related errors
        form = TeamForm()
        logger.info("TeamForm initialized")
        
        # Handle form submission
        if request.method == 'POST':
            if form.validate_on_submit():
                try:
                    # Start a transaction
                    db.session.begin_nested()
                    
                    # Create new team
                    team = Team(
                        name=form.name.data,
                        description=form.description.data,
                        is_active=True
                    )
                    logger.info(f"Created team object with name: {team.name}")
                    
                    # Set leader if selected
                    if form.leader_id.data and form.leader_id.data != 0:
                        leader = User.query.get(form.leader_id.data)
                        if leader:
                            team.leader_id = leader.id
                            logger.info(f"Set team leader: {leader.username}")
                        else:
                            raise ValueError('Selected leader not found')
                    
                    # Set portfolio if selected and portfolio_id exists in Team model
                    if hasattr(Team, 'portfolio_id') and form.portfolio_id.data and form.portfolio_id.data != 0:
                        portfolio = Portfolio.query.get(form.portfolio_id.data)
                        if portfolio:
                            team.portfolio_id = portfolio.id
                            logger.info(f"Set team portfolio: {portfolio.name}")
                        else:
                            raise ValueError('Selected portfolio not found')
                    
                    # Add team to session
                    db.session.add(team)
                    db.session.flush()  # Get team ID
                    logger.info(f"Added team to session with ID: {team.id}")
                    
                    # Add members
                    if form.members.data:
                        for user_id in form.members.data:
                            try:
                                member = User.query.get(user_id)
                                if member:
                                    membership = team.add_member(member)
                                    if membership:
                                        logger.info(f"Added member {member.username} to team")
                                    else:
                                        logger.warning(f"Failed to add member {member.username} to team")
                                else:
                                    logger.warning(f"Member with ID {user_id} not found")
                            except Exception as e:
                                logger.error(f"Error adding member {user_id}: {str(e)}")
                                continue
                    
                    # Commit the transaction
                    db.session.commit()
                    flash('Team created successfully.', 'success')
                    return redirect(url_for('admin.manage_teams'))
                    
                except ValueError as ve:
                    db.session.rollback()
                    logger.warning(f"Validation error in team creation: {str(ve)}")
                    flash(str(ve), 'danger')
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.error(f"Database error in team creation: {str(e)}", exc_info=True)
                    flash('Database error occurred while creating team.', 'danger')
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Unexpected error in team creation: {str(e)}", exc_info=True)
                    flash('An unexpected error occurred while creating team.', 'danger')
            else:
                # Form validation failed
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{getattr(form, field).label.text}: {error}', 'danger')
                        logger.warning(f"Form validation error - {field}: {error}")
        
        # Get all teams for display using raw SQL to avoid model mapping issues
        teams = []
        result = db.session.execute(text("""
            SELECT t.id, t.name, t.description, t.leader_id, t.is_active, t.created_at, t.updated_at,
                   u.username as leader_username, u.display_name as leader_display_name,
                   COUNT(tm.id) as member_count
            FROM teams t
            LEFT JOIN users u ON t.leader_id = u.id
            LEFT JOIN team_memberships tm ON t.id = tm.team_id
            GROUP BY t.id
        """))
        
        for row in result:
            team_dict = {
                'id': row.id,
                'name': row.name,
                'description': row.description,
                'leader': {
                    'username': row.leader_username,
                    'display_name': row.leader_display_name
                } if row.leader_username else None,
                'members_count': row.member_count,
                'is_active': row.is_active,
                'created_at': row.created_at,
                'updated_at': row.updated_at
            }
            teams.append(team_dict)
            
        logger.info(f"Retrieved {len(teams)} teams")
        
        # Render template with teams and form
        return render_template('admin/teams.html', teams=teams, form=form)
        
    except Exception as e:
        logger.error(f"Error in manage_teams view: {str(e)}", exc_info=True)
        flash('An error occurred while managing teams.', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/projects', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_projects():
    """Project management page."""
    try:
        form = ProjectForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                try:
                    project = Project(
                        name=form.name.data,
                        jira_key=form.jira_key.data,
                        description=form.description.data,
                        is_active=form.is_active.data
                    )
                    db.session.add(project)
                    db.session.commit()
                    flash('Project created successfully.', 'success')
                    return redirect(url_for('admin.manage_projects'))
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.error(f"Database error creating project: {str(e)}", exc_info=True)
                    flash('Database error occurred while creating project.', 'danger')
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error creating project: {str(e)}", exc_info=True)
                    flash('An error occurred while creating project.', 'danger')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{getattr(form, field).label.text}: {error}', 'danger')

        projects = Project.query.all()
        return render_template('admin/projects/index.html', projects=projects, form=form)
    except Exception as e:
        logger.error(f"Error in manage_projects view: {str(e)}", exc_info=True)
        flash('An error occurred while managing projects.', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/projects/<int:project_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_project(project_id):
    """Manage specific project."""
    try:
        project = Project.query.get_or_404(project_id)
        
        if request.method == 'GET':
            return jsonify(project.to_dict())
            
        elif request.method == 'PUT':
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No data provided'}), 400
                
            project.name = data.get('name', project.name)
            project.jira_key = data.get('jira_key', project.jira_key)
            project.description = data.get('description', project.description)
            project.is_active = data.get('is_active', project.is_active)
                
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Project updated successfully'})
            
        elif request.method == 'DELETE':
            db.session.delete(project)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Project deleted successfully'})
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing project {project_id}: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """Settings page."""
    try:
        form = SettingsForm()
        
        # Pre-populate form with current settings
        if not form.is_submitted():
            form.sync_interval.data = current_app.config.get('SYNC_INTERVAL', 3600)
            form.log_level.data = str(current_app.config.get('LOG_LEVEL', 20))
            form.cache_timeout.data = current_app.config.get('CACHE_TIMEOUT', 300)
        
        return render_template('admin/settings/index.html', form=form)
    except SQLAlchemyError as e:
        logger.error(f"Database error loading settings: {str(e)}", exc_info=True)
        flash('Database error loading settings.', 'danger')
        return redirect(url_for('admin.index'))
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}", exc_info=True)
        flash('Error loading settings.', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/portfolios')
@login_required
@admin_required
def manage_portfolios():
    """List all portfolios with CRUD actions."""
    try:
        from app.models.portfolio import Portfolio
        
        # Try to migrate schema if needed
        try:
            if Portfolio.migrate_schema():
                logger.info("Portfolio schema migration completed successfully")
            else:
                logger.warning("Portfolio schema migration was not successful")
        except Exception as e:
            logger.warning(f"Schema migration failed (this may be expected if columns already exist): {str(e)}")
        
        try:
            # Try to fetch portfolios
            portfolios = Portfolio.query.all()
            return render_template('admin/portfolios/list.html', portfolios=portfolios)
        except Exception as e:
            # If there's an error fetching portfolios, try running migrations again
            logger.error(f"Error fetching portfolios, attempting to fix schema: {str(e)}")
            db.session.rollback()
            
            # Create tables if they don't exist
            db.create_all()
            
            # Try fetching again
            portfolios = Portfolio.query.all()
            return render_template('admin/portfolios/list.html', portfolios=portfolios)
            
    except Exception as e:
        current_app.logger.error(f"Error in manage_portfolios view: {str(e)}", exc_info=True)
        flash("Error loading portfolios", "error")
        return redirect(url_for('admin.index'))

@admin_bp.route('/portfolios/assignments')
@login_required
@admin_required
def portfolio_assignments():
    """Manage portfolio-to-project assignments."""
    try:
        from app.models.portfolio import Portfolio
        portfolios = Portfolio.query.all()
        return render_template('admin/portfolios/assignments.html', portfolios=portfolios)
    except Exception as e:
        current_app.logger.error(f"Error loading portfolio assignments: {str(e)}", exc_info=True)
        import traceback
        current_app.logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        flash("Error loading portfolio assignments", "error")
        return redirect(url_for('admin.index'))

@admin_bp.route('/portfolios/analysis')
@login_required
@admin_required
def portfolio_analysis():
    """Display analytics for portfolios (planned vs actual hours)."""
    try:
        # For demonstration, we pass dummy aggregated data.
        analysis_data = {
             "total_hours": 1200,
             "planned_hours": 1500,
             "actual_hours": 1200,
             "discrepancy": 300
        }
        from app.models.portfolio import Portfolio
        portfolios = Portfolio.query.all()
        return render_template('admin/portfolios/analysis.html',
                                portfolios=portfolios,
                                analysis_data=analysis_data)
    except Exception as e:
        current_app.logger.error(f"Error loading portfolio analysis: {str(e)}")
        flash("Error loading portfolio analysis", "error")
        return redirect(url_for('admin.index'))

@admin_bp.route('/portfolios/seed')
@login_required
@admin_required
def seed_portfolios():
    """Endpoint służący do seeding'u przykładowych danych portfolio."""
    try:
        from app.models.portfolio import Portfolio
        # Upewnij się, że model Portfolio nie wymaga innych pól (np. created_at, updated_at, itp.)
        if Portfolio.query.count() == 0:
            new_portfolio = Portfolio(
                name="Test Portfolio",
                description="Przykładowe portfolio"
                # Dodaj inne wymagane pola, jeśli istnieją, np.: created_at=datetime.utcnow()
            )
            db.session.add(new_portfolio)
            db.session.commit()
            flash("Przykładowe portfolio dodane.", "success")
        else:
            flash("Portfolio już istnieje.", "info")
    except Exception as e:
        current_app.logger.error(f"Error seeding portfolios: {str(e)}")
        flash(f"Błąd przy dodawaniu przykładowych danych: {e}", "error")
    return redirect(url_for('admin.manage_portfolios'))

@admin_bp.route('/system-settings', methods=['POST'])
@login_required
@admin_required
def save_system_settings():
    """Save system settings."""
    form = SystemSettingsForm()
    if form.validate_on_submit():
        try:
            current_app.config.update(
                SYSTEM_NAME=form.system_name.data,
                ADMIN_EMAIL=form.admin_email.data
            )
            flash('System settings saved successfully', 'success')
            return redirect(url_for('admin.settings'))
        except Exception as e:
            logger.error(f"Error saving system settings: {str(e)}")
            flash('Error saving system settings', 'error')
    
    return redirect(url_for('admin.settings'))

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """System logs page."""
    return render_template('admin/logs.html')

@admin_bp.route('/email-settings')
@login_required
@admin_required
def email_settings():
    return render_template('admin/email_settings.html')

@admin_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """Get all users with their details."""
    try:
        users = User.query.all()
        return jsonify({
            'status': 'success',
            'users': [user.to_dict() for user in users]
        })
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """Get user details."""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create new user."""
    try:
        data = request.get_json()
        new_user = User(
            username=data['username'],
            email=data['email'],
            display_name=data.get('display_name', ''),
            is_active=data.get('is_active', True)
        )
        new_user.set_password(data.get('password', 'changeme'))
        db.session.add(new_user)
        db.session.flush()  # To get the user ID
        
        # Add roles from request or ensure default role
        if 'roles' in data:
            for role_id in data['roles']:
                role = Role.query.get(role_id)
                if role:
                    new_user.add_role(role)
        else:
            new_user.ensure_default_role()

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'User created successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Update user."""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        # Aktualizuj podstawowe dane
        user.username = data.get('username', user.username)
        user.email = data.get('email', user.email)
        user.display_name = data.get('display_name')
        user.is_active = data.get('is_active', user.is_active)

        # Aktualizuj role
        if 'roles' in data:
            # Usuń wszystkie obecne role
            user.user_roles = []
            
            # Dodaj nowe role
            for role_id in data['roles']:
                role = Role.query.get(role_id)
                if role:
                    user.add_role(role)

        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'User updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/users/<user_name>', methods=['DELETE'])
@admin_required
def delete_user(user_name):
    """Usuwa użytkownika."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Sprawdź czy użytkownik istnieje
        cursor.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,))
        if not cursor.fetchone():
            return jsonify({"error": "Użytkownik nie istnieje"}), 404
            
        # Usuń powiązane rekordy
        cursor.execute("DELETE FROM user_roles WHERE user_name = ?", (user_name,))
        cursor.execute("DELETE FROM users WHERE user_name = ?", (user_name,))
        
        db.commit()
        
        return jsonify({"message": "Użytkownik został usunięty"})
        
    except Exception as e:
        logger.error(f"Error deleting user {user_name}: {str(e)}")
        return jsonify({"error": "Błąd podczas usuwania użytkownika"}), 500

@admin_bp.route('/sync/jira', methods=['POST'])
@login_required
@admin_required
def sync_all_jira():
    """Synchronize all JIRA data."""
    try:
        logger.info("Starting full JIRA synchronization")
        jira_service = get_jira_service()
        
        if not jira_service:
            logger.error("Failed to get JIRA service")
            return jsonify({
                'status': 'error',
                'message': 'Could not initialize JIRA service'
            }), 500
            
        if not jira_service.is_connected:
            logger.error("JIRA service is not connected")
            return jsonify({
                'status': 'error',
                'message': 'Not connected to JIRA. Please check your configuration.'
            }), 400

        success, results = jira_service.sync_all()
        
        if success:
            logger.info(f"Full sync completed successfully: {results}")
            return jsonify({
                'status': 'success',
                'message': 'Full synchronization completed successfully',
                'stats': results
            })
        else:
            logger.error(f"Full sync failed: {results.get('error', 'Unknown error')}")
            return jsonify({
                'status': 'error',
                'message': results.get('error', 'Synchronization failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Error in full sync: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/sync/users', methods=['POST'])
@login_required
@admin_required
def sync_users():
    """Synchronize users from JIRA."""
    try:
        jira_service = get_jira_service()
        if not jira_service or not jira_service.is_configured:
            return jsonify({
                'status': 'error',
                'message': 'JIRA is not configured'
            }), 400

        stats = jira_service.sync_users()
        logger.info(f"Sync completed with stats: {stats}")

        return jsonify({
            'status': 'success',
            'message': f"Successfully synchronized {stats['total']} users",
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error in sync_jira_users: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Error synchronizing users: {str(e)}"
        }), 500

@admin_bp.route('/sync-projects', methods=['POST'])
@admin_bp.route('/sync/projects', methods=['POST'])
@login_required
@admin_required
def sync_projects():
    """Synchronize projects from JIRA."""
    try:
        logger.info("Starting JIRA project synchronization")
        jira_service = get_jira_service()
        
        if not jira_service:
            logger.error("Failed to get JIRA service")
            return jsonify({
                'status': 'error',
                'message': 'Could not initialize JIRA service'
            }), 500
            
        if not jira_service.is_connected:
            logger.error("JIRA service is not connected")
            return jsonify({
                'status': 'error',
                'message': 'Not connected to JIRA. Please check your configuration.'
            }), 400

        stats = jira_service.sync_projects()
        logger.info(f"Project sync completed: {stats}")
        
        return jsonify({
            'status': 'success',
            'message': 'Project synchronization completed successfully',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error syncing projects: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/sync/worklogs', methods=['POST'])
@login_required
@admin_required
def sync_worklogs():
    """Synchronize worklogs from JIRA."""
    try:
        logger.info("Starting JIRA worklog synchronization")
        jira_service = get_jira_service()
        
        if not jira_service:
            logger.error("Failed to get JIRA service")
            return jsonify({
                'status': 'error',
                'message': 'Could not initialize JIRA service'
            }), 500
            
        if not jira_service.is_connected:
            logger.error("JIRA service is not connected")
            return jsonify({
                'status': 'error',
                'message': 'Not connected to JIRA. Please check your configuration.'
            }), 400

        stats = jira_service.sync_worklogs()
        logger.info(f"Worklog sync completed: {stats}")
        
        return jsonify({
            'status': 'success',
            'message': 'Worklog synchronization completed successfully',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error syncing worklogs: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/api/jira-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def jira_settings_api():
    if request.method == 'POST':
        data = request.get_json()
        current_app.config.update(
            JIRA_URL=data.get('url'),
            JIRA_USERNAME=data.get('username'),
            JIRA_API_TOKEN=data.get('api_token'),
            JIRA_PROJECT_KEYS=data.get('project_keys', '').split(',')
        )
        return jsonify({"message": "Settings updated successfully"})
    
    return jsonify({
        "url": current_app.config.get('JIRA_URL'),
        "username": current_app.config.get('JIRA_USERNAME'),
        "project_keys": ','.join(current_app.config.get('JIRA_PROJECT_KEYS', []))
    })

@admin_bp.route('/api/system-stats')
@login_required
@admin_required
def system_stats_api():
    stats = {
        "users_count": User.query.count(),
        "active_users": User.query.filter_by(is_active=True).count(),
        "roles_count": Role.query.count(),
        "teams_count": Team.query.count(),
        "portfolios_count": Portfolio.query.count()
    }
    return jsonify(stats)

@admin_bp.route('/cache/clear', methods=['POST'])
@login_required
@admin_required
def clear_cache():
    """Czyści cache aplikacji."""
    try:
        cache.clear()
        logger.info("Cache cleared successfully")
        return jsonify({
            'status': 'success',
            'message': 'Cache wyczyszczony pomyślnie'
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Wystąpił błąd podczas czyszczenia cache'
        }), 500

@admin_bp.route('/api/jira/projects', methods=['GET'])
@login_required
@admin_required
def get_jira_projects_api():
    """Get projects from JIRA."""
    try:
        projects = get_jira_projects()
        if projects:
            return jsonify({
                'status': 'success',
                'projects': projects,
                'count': len(projects)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No projects found or JIRA connection error'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting JIRA projects: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/api/sync/jira/status', methods=['GET'])
@login_required
@admin_required
def get_sync_status():
    """Endpoint do sprawdzania statusu ostatniej synchronizacji."""
    try:
        jira_config = JiraConfig.query.filter_by(is_active=True).first()
        if not jira_config:
            return jsonify({
                'status': 'error',
                'message': 'Brak konfiguracji JIRA'
            }), 404
            
        return jsonify({
            'status': 'success',
            'last_sync': jira_config.updated_at.isoformat() if jira_config.updated_at else None,
            'is_active': jira_config.is_active
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/jira')
def jira():
    """JIRA configuration page."""
    return render_template('admin/jira.html')

@admin_bp.route('/jira/sync-users', methods=['POST'])
@login_required
@admin_required
def sync_jira_users():
    """Synchronize users from JIRA."""
    try:
        jira_service = get_jira_service()
        if not jira_service or not jira_service.is_configured:
            return jsonify({
                'status': 'error',
                'message': 'JIRA is not configured'
            }), 400

        stats = jira_service.sync_users()
        logger.info(f"Sync completed with stats: {stats}")

        return jsonify({
            'status': 'success',
            'message': f"Successfully synchronized {stats['total']} users",
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error in sync_jira_users: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Error synchronizing users: {str(e)}"
        }), 500

@admin_bp.route('/static/<path:filename>')
def static_files(filename):
    """Obsługa plików statycznych."""
    return send_from_directory(
        current_app.static_folder,  # Używamy static_folder z konfiguracji
        filename,
        cache_timeout=0  # Podczas developmentu
    )

@admin_bp.route('/api/jira/fetch-users', methods=['GET'])
@login_required
@admin_required
def fetch_jira_users():
    try:
        start_at = request.args.get('startAt', type=int, default=0)
        max_results = request.args.get('maxResults', type=int, default=50)
        
        jira_service = JiraService()
        users = jira_service.get_users(start_at=start_at, max_results=max_results)
        
        return jsonify(users)
    except Exception as e:
        current_app.logger.error(f"Error fetching JIRA users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/jira/import', methods=['POST'])
@login_required
@admin_required
def jira_import():
    try:
        data = request.get_json()
        if not data or 'users' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Brak danych użytkowników'
            }), 400

        jira_service = JiraService()
        result = jira_service.import_users(data['users'])

        return jsonify({
            'status': 'success',
            'message': f"Zaimportowano {len(data['users'])} użytkowników",
            'details': result
        })

    except Exception as e:
        current_app.logger.error(f"Błąd podczas importu użytkowników: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/users/import', methods=['POST'])
@login_required
@admin_required
def import_users() -> Dict[str, Any]:
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files are supported'}), 400

    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        csv_reader = csv.DictReader(stream)
        
        imported_users = []
        for row in csv_reader:
            # Add validation and processing logic here
            imported_users.append(row)
        
        # Process the imported users
        for user_data in imported_users:
            user = User(
                username=user_data.get('username'),
                email=user_data.get('email'),
                display_name=user_data.get('display_name', ''),
                is_active=True
            )
            user.set_password('changeme')  # Set default password
            db.session.add(user)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully imported {len(imported_users)} users',
            'imported_count': len(imported_users)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing users: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Failed to process CSV file',
            'details': str(e)
        }), 400

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Reports dashboard page."""
    return render_template('admin/reports/index.html')

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """System analytics view."""
    return render_template('admin/analytics.html')

@admin_bp.route('/jira-config', methods=['GET', 'POST'])
@login_required
@admin_required
def jira_config():
    """JIRA configuration view."""
    form = JiraSettingsForm()
    config = JiraConfig.query.filter_by(is_active=True).first()

    if request.method == 'POST':
        if 'reset' in request.form:
            try:
                # Delete all existing configurations
                JiraConfig.query.delete()
                db.session.commit()
                flash('JIRA configuration has been reset successfully.', 'success')
                return redirect(url_for('admin.jira_config'))
            except Exception as e:
                logger.error(f"Error resetting JIRA config: {str(e)}")
                db.session.rollback()
                flash('Failed to reset JIRA configuration.', 'error')
                return redirect(url_for('admin.jira_config'))

        if form.validate():
            try:
                # Create new config
                new_config = JiraConfig(
                    url=form.url.data,
                    username=form.username.data,
                    password=form.password.data,
                    is_active=True
                )

                # Test connection before saving
                try:
                    new_config.validate_connection()
                except Exception as e:
                    flash(f'Connection test failed: {str(e)}', 'error')
                    return render_template('admin/jira_config.html', form=form, config=config, is_connected=False)

                # Delete any existing configurations
                JiraConfig.query.delete()
                
                # Save new configuration
                db.session.add(new_config)
                db.session.commit()

                # Reinitialize JIRA service
                jira_service = get_jira_service()
                if jira_service:
                    jira_service.initialize()

                flash('JIRA configuration saved and connection tested successfully.', 'success')
                return redirect(url_for('admin.jira_config'))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving JIRA config: {str(e)}")
                flash(f'Error saving configuration: {str(e)}', 'error')

    # Check JIRA connection status for GET request
    is_connected = False
    if config:
        try:
            jira_service = get_jira_service()
            is_connected = jira_service and jira_service.is_configured
            if is_connected:
                form.url.data = config.url
                form.username.data = config.username
                form.is_active.data = config.is_active
        except Exception as e:
            logger.error(f"Error checking JIRA connection: {str(e)}")

    return render_template('admin/jira_config.html', form=form, config=config, is_connected=is_connected)

@admin_bp.route('/jira/test-connection', methods=['POST'])
@login_required
@admin_required
def test_jira_connection():
    """Test JIRA connection."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Missing configuration data'
            }), 400

        # Create temporary config for testing
        config = JiraConfig(
            url=data.get('url'),
            username=data.get('username'),
            password=data.get('password')  # Changed from api_token to password
        )
        
        try:
            config.validate_connection()
            return jsonify({
                'status': 'success',
                'message': 'Connection successful'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"Error testing JIRA connection: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/activity-report')
@login_required
@admin_required
def activity_report():
    """Generate activity report."""
    try:
        # Implementacja raportu aktywności
        return render_template('admin/activity_report.html')
    except Exception as e:
        logger.error(f"Error generating activity report: {str(e)}")
        flash('Błąd podczas generowania raportu aktywności.', 'danger')
        return redirect(url_for('admin.reports'))

@admin_bp.route('/performance-report')
@login_required
@admin_required
def performance_report():
    """Generate performance report."""
    try:
        # Implementacja raportu wydajności
        return render_template('admin/performance_report.html')
    except Exception as e:
        logger.error(f"Error generating performance report: {str(e)}")
        flash('Błąd podczas generowania raportu wydajności.', 'danger')
        return redirect(url_for('admin.reports'))

@admin_bp.route('/worklogs')
@login_required
@admin_required
def manage_worklogs():
    """Worklog management page."""
    try:
        users = User.query.filter_by(is_active=True).order_by(User.display_name).all()
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
        
        # Domyślnie pokaż worklogi z ostatnich 7 dni
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Podstawowe zapytanie z eager loading
        query = Worklog.query\
            .options(
                db.joinedload(Worklog.user),
                db.joinedload(Worklog.project),
                db.joinedload(Worklog.issue)
            )\
            .filter(Worklog.work_date.between(start_date, end_date))\
            .order_by(Worklog.work_date.desc())
        
        worklogs = query.limit(100).all()
        
        return render_template(
            'admin/worklogs/index.html',
            users=users,
            projects=projects,
            worklogs=worklogs,
            default_date_range={
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        )
    except Exception as e:
        logger.error(f"Error in manage_worklogs view: {str(e)}")
        flash('Error loading worklogs', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/worklogs/data')
@login_required
@admin_required
def get_worklogs_data():
    """Get worklog data with filters and statistics."""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        project_id = request.args.get('project_id')
        user_id = request.args.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Base query for statistics
        stats_query = db.session.query(
            db.func.count(Worklog.id).label('total_count'),
            db.func.sum(Worklog.time_spent_seconds).label('total_time'),
            db.func.count(db.distinct(Worklog.user_id)).label('active_users')
        )

        # Base query for data
        base_query = Worklog.query\
            .join(Worklog.user)\
            .join(Worklog.project)\
            .join(Worklog.issue)

        # Apply filters to both queries
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            base_query = base_query.filter(Worklog.work_date >= start_date)
            stats_query = stats_query.filter(Worklog.work_date >= start_date)

        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            base_query = base_query.filter(Worklog.work_date <= end_date)
            stats_query = stats_query.filter(Worklog.work_date <= end_date)

        if project_id:
            base_query = base_query.filter(Worklog.project_id == project_id)
            stats_query = stats_query.filter(Worklog.project_id == project_id)

        if user_id:
            base_query = base_query.filter(Worklog.user_id == user_id)
            stats_query = stats_query.filter(Worklog.user_id == user_id)

        # Get statistics
        stats = stats_query.first()
        total_count = stats.total_count or 0
        total_hours = round((stats.total_time or 0) / 3600, 2)
        active_users = stats.active_users or 0

        # Calculate average daily hours if date range is provided
        avg_daily_hours = 0
        if start_date and end_date:
            days = (end_date - start_date).days + 1
            if days > 0:
                avg_daily_hours = round(total_hours / days, 2)

        # Apply sorting and pagination to data query
        sort_column = request.args.get('sort', 'work_date')
        sort_dir = request.args.get('order', 'desc')

        if sort_column == 'user':
            sort_field = User.display_name
        elif sort_column == 'project':
            sort_field = Project.name
        elif sort_column == 'issue':
            sort_field = Issue.jira_key
        else:
            sort_field = getattr(Worklog, sort_column)

        if sort_dir == 'desc':
            base_query = base_query.order_by(sort_field.desc())
        else:
            base_query = base_query.order_by(sort_field.asc())

        # Get paginated results
        pagination = base_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Prepare worklog data
        worklogs = []
        for worklog in pagination.items:
            worklogs.append({
                'id': worklog.id,
                'user': {
                    'id': worklog.user.id,
                    'name': worklog.user.display_name or worklog.user.username
                },
                'project': {
                    'id': worklog.project.id,
                    'name': worklog.project.name,
                    'key': worklog.project.jira_key
                },
                'issue': {
                    'id': worklog.issue.id,
                    'key': worklog.issue.jira_key,
                    'summary': worklog.issue.summary
                },
                'time_spent_seconds': worklog.time_spent_seconds,
                'time_spent_hours': round(worklog.time_spent_seconds / 3600, 2),
                'work_date': worklog.work_date.strftime('%Y-%m-%d'),
                'description': worklog.description,
                'created_at': worklog.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify({
            'status': 'success',
            'data': {
                'worklogs': worklogs,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'total': pagination.total,
                    'per_page': pagination.per_page
                },
                'stats': {
                    'total_count': total_count,
                    'total_hours': total_hours,
                    'active_users': active_users,
                    'avg_daily_hours': avg_daily_hours
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting worklog data: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/worklogs/<int:worklog_id>')
@login_required
@admin_required
def get_worklog(worklog_id):
    """Get worklog details."""
    try:
        worklog = Worklog.query\
            .options(
                db.joinedload(Worklog.user),
                db.joinedload(Worklog.project),
                db.joinedload(Worklog.issue)
            )\
            .get_or_404(worklog_id)
        return jsonify(worklog.to_dict())
    except Exception as e:
        logger.error(f"Error getting worklog {worklog_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/worklogs/<int:worklog_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_worklog(worklog_id):
    """Delete worklog."""
    try:
        worklog = Worklog.query.get_or_404(worklog_id)
        db.session.delete(worklog)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Worklog deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting worklog {worklog_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/reports/workload')
@login_required
@admin_required
def workload_report():
    return render_template('admin/reports/workload.html')

@admin_bp.route('/reports/role-distribution')
@login_required
@admin_required
def role_distribution_report():
    return render_template('admin/reports/role_distribution.html')

@admin_bp.route('/reports/availability')
@login_required
@admin_required
def availability_report():
    return render_template('admin/reports/availability.html')

@admin_bp.route('/reports/shadow-work')
@login_required
@admin_required
def shadow_work_report():
    return render_template('admin/reports/shadow_work.html')

@admin_bp.route('/reports/custom')
@login_required
@admin_required
def custom_reports():
    return render_template('admin/reports/custom.html')

@admin_bp.route('/user/availability')
@login_required
def user_availability():
    """User availability page."""
    return render_template('admin/user/availability.html')

@admin_bp.route('/user/leave-requests')
@login_required
def leave_requests():
    """User leave requests page."""
    try:
        # User-facing view: simple leave request list
        leave_request_list = LeaveRequest.query.all()
        return render_template('admin/leave_requests.html', leave_requests=leave_request_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f'Error loading leave requests: {e}')
        return render_template('errors/500.html'), 500

@admin_bp.route('/leave-management', methods=['GET', 'POST'])
@login_required
@admin_required
def leave_management():
    try:
        from app.models.leave_request import LeaveRequest
        leave_request_list = LeaveRequest.query.order_by(LeaveRequest.start_date).all()

        if request.method == 'POST':
            # CSV Import logic: process the uploaded CSV file.
            if 'csv_file' in request.files:
                csv_file = request.files['csv_file']
                # TODO: Parse the CSV file and update the database accordingly.
                flash("CSV file imported successfully.", "success")
            else:
                flash("No CSV file uploaded.", "danger")

        return render_template('admin/leave_management.html', leave_requests=leave_request_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f'Error loading leave management: {e}')
        return render_template('errors/500.html'), 500

@admin_bp.route('/leave-management/<int:leave_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_leave_request(leave_id: int):
    """Endpoint to edit a leave request."""
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        if request.method == 'POST':
            # Update the leave details from the submitted form
            leave.start_date = request.form.get('start_date', leave.start_date)
            leave.end_date = request.form.get('end_date', leave.end_date)
            leave.leave_type = request.form.get('leave_type', leave.leave_type)
            leave.reason = request.form.get('reason', leave.reason)
            db.session.commit()
            flash("Leave request updated successfully", "success")
            return redirect(url_for('admin.leave_management'))
        return render_template('admin/edit_leave_request.html', leave=leave)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error editing leave request {leave_id}: {e}")
        flash("Error editing leave request", "danger")
        return redirect(url_for('admin.leave_management'))

@admin_bp.route('/leave-management/<int:leave_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_leave_request(leave_id: int):
    """Endpoint to delete a leave request."""
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        db.session.delete(leave)
        db.session.commit()
        flash("Leave request deleted successfully", "success")
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error deleting leave request {leave_id}: {e}")
        flash("Error deleting leave request", "danger")
    return redirect(url_for('admin.leave_management'))

@admin_bp.route('/leave-management/<int:leave_id>/status', methods=['POST'])
@login_required
@admin_required
def update_leave_status(leave_id: int):
    """AJAX endpoint to update leave status (approve or reject)."""
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        data = request.get_json()
        new_status = data.get("status")
        if new_status not in ["approved", "rejected"]:
            return jsonify({"status": "error", "message": "Invalid status."}), 400
        leave.status = new_status
        leave.approved_by = current_user.id
        leave.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"status": "success", "message": f"Leave request {new_status} successfully."})
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error updating leave status for request {leave_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """Audit logs page."""
    return render_template('admin/audit_logs.html')

@admin_bp.route('/logs/data')
@login_required
@admin_required
def get_logs_data():
    """Get logs data."""
    try:
        # Pobierz parametry filtrowania
        level = request.args.get('level')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Przeczytaj logi z pliku
        log_file = Path(current_app.instance_path) / 'logs' / 'app.log'
        if not log_file.exists():
            return jsonify([])
            
        logs = []
        with open(log_file, 'r') as f:
            for line in f:
                # Parsuj linię logu
                try:
                    timestamp = line[:19]
                    level_start = line.find('[') + 1
                    level_end = line.find(']', level_start)
                    log_level = line[level_start:level_end].strip()
                    message = line[level_end + 1:].strip()
                    
                    # Filtruj po poziomie
                    if level and log_level.lower() != level.lower():
                        continue
                        
                    # Filtruj po dacie
                    log_date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    if start_date:
                        start = datetime.strptime(start_date, '%Y-%m-%d')
                        if log_date < start:
                            continue
                    if end_date:
                        end = datetime.strptime(end_date, '%Y-%m-%d')
                        if log_date > end:
                            continue
                            
                    logs.append({
                        'timestamp': timestamp,
                        'level': log_level,
                        'message': message
                    })
                except Exception as e:
                    logger.error(f"Error parsing log line: {str(e)}")
                    continue
                    
        return jsonify(logs)
        
    except Exception as e:
        logger.error(f"Error getting logs data: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    stats = get_admin_stats()
    recent_activities = get_recent_activities()
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_activities=recent_activities)

def get_recent_activities(limit=10):
    """Get recent system activities."""
    try:
        # Tu dodaj logikę pobierania ostatnich aktywności z bazy danych
        # Na razie zwracamy przykładowe dane
        return [
            {
                'title': 'New user registered',
                'description': 'User John Doe created an account',
                'timestamp': datetime.now(),
                'user': 'System'
            },
            {
                'title': 'Project updated',
                'description': 'Project "Sample Project" was updated',
                'timestamp': datetime.now(),
                'user': 'Admin'
            }
        ]
    except Exception as e:
        logger.error(f"Error getting recent activities: {str(e)}")
        return [] 

@admin_bp.route('/leave-management/data')
@login_required
@admin_required
def get_leave_data():
    """Get filtered leave requests data."""
    try:
        status = request.args.get('status')
        date_range = request.args.get('date_range')
        user_id = request.args.get('user_id')
        
        query = LeaveRequest.query
        
        if status:
            query = query.filter(LeaveRequest.status == status)
        if user_id:
            query = query.filter(LeaveRequest.user_id == user_id)
        if date_range:
            start_date, end_date = date_range.split(' - ')
            query = query.filter(
                LeaveRequest.start_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
                LeaveRequest.end_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
            )
            
        leave_requests = query.all()
        return jsonify({
            'status': 'success',
            'leave_requests': [request.to_dict() for request in leave_requests]
        })
    except Exception as e:
        logger.error(f"Error getting leave data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@admin_bp.route('/leave-management/<int:leave_id>')
@login_required
@admin_required
def get_leave_details(leave_id):
    """Get leave request details."""
    try:
        leave = LeaveRequest.query.get_or_404(leave_id)
        return jsonify(leave.to_dict())
    except Exception as e:
        logger.error(f"Error getting leave details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 

@admin_bp.route('/portfolios/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_portfolio():
    """Create new portfolio."""
    form = PortfolioForm()
    
    if request.method == 'POST':
        # Log request data for debugging
        logger.debug(f"Form data: {request.form}")
        logger.debug(f"CSRF token in form: {request.form.get('csrf_token')}")
        logger.debug(f"CSRF token in session: {session.get('csrf_token')}")
        
        if form.validate_on_submit():
            try:
                portfolio = Portfolio(
                    name=form.name.data,
                    description=form.description.data,
                    is_active=True,
                    created_by=current_user.username
                )
                
                # Add selected projects if any
                if form.projects.data:
                    from app.models.project import Project
                    for project_id in form.projects.data:
                        project = Project.query.get(project_id)
                        if project:
                            portfolio.projects.append(project)
                
                db.session.add(portfolio)
                db.session.commit()
                flash('Portfolio zostało utworzone.', 'success')
                return redirect(url_for('admin.manage_portfolios'))
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error creating portfolio: {str(e)}")
                flash('Błąd bazy danych podczas tworzenia portfolio.', 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')
                    logger.error(f"Form validation error - {field}: {error}")
    
    # Generate new CSRF token for GET requests
    if request.method == 'GET':
        form.csrf_token.data = generate_csrf()
    
    return render_template('admin/portfolios/create.html', form=form)

@admin_bp.route('/portfolios/<int:portfolio_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_portfolio(portfolio_id):
    """Edit existing portfolio."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        form = PortfolioForm(obj=portfolio)
        
        if form.validate_on_submit():
            portfolio.name = form.name.data
            portfolio.description = form.description.data
            db.session.commit()
            flash('Portfolio zostało zaktualizowane.', 'success')
            return redirect(url_for('admin.manage_portfolios'))
            
        return render_template('admin/portfolios/edit.html', form=form, portfolio=portfolio)
    except Exception as e:
        current_app.logger.error(f"Error editing portfolio {portfolio_id}: {str(e)}")
        flash('Błąd podczas edycji portfolio.', 'error')
        return redirect(url_for('admin.manage_portfolios'))

@admin_bp.route('/portfolios/<int:portfolio_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_portfolio(portfolio_id):
    """Delete portfolio."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        db.session.delete(portfolio)
        db.session.commit()
        flash('Portfolio zostało usunięte.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting portfolio {portfolio_id}: {str(e)}")
        flash('Błąd podczas usuwania portfolio.', 'error')
    return redirect(url_for('admin.manage_portfolios'))

@admin_bp.route('/portfolios/<int:portfolio_id>/projects', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_portfolio_projects(portfolio_id):
    """Manage projects in portfolio."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        if request.method == 'POST':
            project_id = request.form.get('project_id')
            action = request.form.get('action')
            
            if not project_id or not action:
                return jsonify({'status': 'error', 'message': 'Brak wymaganych parametrów'}), 400
                
            project = Project.query.get_or_404(project_id)
            
            if action == 'add':
                if portfolio.add_project(project):
                    db.session.commit()
                    return jsonify({'status': 'success', 'message': 'Projekt dodany do portfolio'})
                return jsonify({'status': 'error', 'message': 'Projekt już jest w portfolio'})
                
            elif action == 'remove':
                if portfolio.remove_project(project):
                    db.session.commit()
                    return jsonify({'status': 'success', 'message': 'Projekt usunięty z portfolio'})
                return jsonify({'status': 'error', 'message': 'Projekt nie jest w portfolio'})
                
            return jsonify({'status': 'error', 'message': 'Nieprawidłowa akcja'}), 400
            
        # GET request
        available_projects = Project.query.filter(~Project.portfolios.any(Portfolio.id == portfolio_id)).all()
        return render_template('admin/portfolios/projects.html',
                             portfolio=portfolio,
                             available_projects=available_projects)
                             
    except Exception as e:
        current_app.logger.error(f"Error managing portfolio projects: {str(e)}")
        flash('Błąd podczas zarządzania projektami w portfolio.', 'error')
        return redirect(url_for('admin.manage_portfolios')) 

@admin_bp.route('/portfolios/<int:portfolio_id>/assignments/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_portfolio_assignments(portfolio_id):
    """Edit portfolio project assignments."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        if request.method == 'POST':
            project_ids = request.form.getlist('project_ids')
            # Clear existing assignments
            portfolio.projects = []
            # Add new assignments
            for project_id in project_ids:
                project = Project.query.get(project_id)
                if project:
                    portfolio.projects.append(project)
            db.session.commit()
            flash('Przypisania projektów zostały zaktualizowane.', 'success')
            return redirect(url_for('admin.portfolio_assignments'))
            
        available_projects = Project.query.all()
        return render_template('admin/portfolios/edit_assignments.html',
                             portfolio=portfolio,
                             available_projects=available_projects)
                             
    except Exception as e:
        current_app.logger.error(f"Error editing portfolio assignments: {str(e)}")
        flash('Błąd podczas edycji przypisań portfolio.', 'error')
        return redirect(url_for('admin.portfolio_assignments')) 

@admin_bp.route('/jira/sync', methods=['POST'])
@login_required
@admin_required
def sync_jira():
    """Synchronize data with JIRA."""
    try:
        jira_service = JiraService()
        success, results = jira_service.sync_all()
        
        if success:
            flash('JIRA synchronization completed successfully.', 'success')
            return jsonify({
                'status': 'success',
                'message': 'Synchronization completed successfully',
                'results': results
            })
        else:
            error_msg = 'JIRA synchronization completed with errors. Check logs for details.'
            if results.get('errors'):
                error_msg = f"Errors occurred: {', '.join(results['errors'])}"
            flash(error_msg, 'error')
            return jsonify({
                'status': 'error',
                'message': error_msg,
                'results': results
            }), 400
            
    except Exception as e:
        error_msg = f'Error during JIRA synchronization: {str(e)}'
        logger.error(error_msg)
        flash(error_msg, 'error')
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500 

@admin_bp.route('/jira/test-sync', methods=['GET'])
@login_required
@admin_required
def test_jira_sync():
    """Test JIRA synchronization and return detailed diagnostics."""
    try:
        results = {
            'jira_config': None,
            'connection_test': None,
            'jira_service': None,
            'test_issue': None,
            'test_worklog': None,
            'errors': []
        }

        # 1. Check JIRA configuration
        try:
            config = JiraConfig.query.filter_by(is_active=True).first()
            if config:
                results['jira_config'] = {
                    'url': config.url,
                    'username': config.username,
                    'has_password': bool(config.password),
                    'is_active': config.is_active,
                    'last_sync': config.last_sync.isoformat() if config.last_sync else None
                }
            else:
                results['errors'].append("No active JIRA configuration found")
        except Exception as e:
            results['errors'].append(f"Error checking JIRA config: {str(e)}")

        # 2. Test JIRA connection
        try:
            jira_service = get_jira_service()
            if jira_service:
                results['jira_service'] = {
                    'initialized': True,
                    'is_connected': jira_service.is_connected
                }
                
                # Test connection
                jira = jira_service.jira
                if jira:
                    server_info = jira.server_info()
                    results['connection_test'] = {
                        'success': True,
                        'version': server_info.get('version', 'unknown'),
                        'base_url': server_info.get('baseUrl', 'unknown')
                    }
                    
                    # Try to get a test issue
                    try:
                        issues = jira.search_issues('updated >= -1d', maxResults=1)
                        if issues:
                            issue = issues[0]
                            results['test_issue'] = {
                                'key': issue.key,
                                'summary': issue.fields.summary,
                                'project': issue.fields.project.key
                            }
                            
                            # Try to get worklogs
                            try:
                                worklogs = jira.worklogs(issue.id)
                                results['test_worklog'] = {
                                    'count': len(worklogs),
                                    'sample': {
                                        'id': worklogs[0].id,
                                        'author': worklogs[0].author.displayName,
                                        'time_spent': worklogs[0].timeSpentSeconds
                                    } if worklogs else None
                                }
                            except Exception as e:
                                results['errors'].append(f"Error getting worklogs: {str(e)}")
                    except Exception as e:
                        results['errors'].append(f"Error getting test issue: {str(e)}")
            else:
                results['errors'].append("Could not initialize JIRA service")
        except Exception as e:
            results['errors'].append(f"Error testing JIRA connection: {str(e)}")

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error in test_jira_sync: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500 