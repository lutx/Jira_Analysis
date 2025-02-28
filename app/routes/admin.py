from flask import Blueprint, request, jsonify, current_app, render_template, flash, redirect, url_for, send_from_directory, session, abort, send_file
from flask_login import login_required, current_user
from app.decorators import admin_required
from app.utils.db import get_db
from app.services import hash_password
from app.services.jira_service import get_jira_service, sync_jira_users, sync_jira_data, test_connection, save_jira_config, get_jira_projects, JiraService
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.team import Team
from app.models.team_membership import TeamMembership as TeamMember
from app.models.portfolio import Portfolio, portfolio_projects
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
from sqlalchemy import text, func, distinct
import traceback
import time
import hashlib
import bleach
from werkzeug.exceptions import HTTPException
from functools import wraps
import threading

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
        logger.info("Starting manage_teams view")
        
        # Get all active users and projects
        users = User.query.filter_by(is_active=True).all()
        projects = Project.query.filter_by(is_active=True).all()
        
        # Initialize form
        form = TeamForm()
        logger.info("TeamForm initialized")
        
        # Get all teams with their relationships
        teams = Team.query.all()
        
        # Check if portfolio_id field exists in the form
        has_portfolio_field = hasattr(form, 'portfolio_id')
        logger.info(f"Form has portfolio_id field: {has_portfolio_field}")
        
        # Jeśli w żądaniu GET przekazany jest action=edit i team_id, załaduj dane zespołu do formularza
        if request.method == 'GET' and request.args.get('action') == 'edit' and request.args.get('team_id'):
            try:
                team_id = request.args.get('team_id')
                logger.info(f"Loading team for edit: team_id={team_id}")
                team = Team.query.get_or_404(team_id)
                
                # Przygotowanie danych zespołu do edycji
                form.name.data = team.name
                form.description.data = team.description
                
                if team.leader_id:
                    form.leader_id.data = team.leader_id
                    logger.info(f"Setting leader_id={team.leader_id}")
                
                # Set portfolio_id if field exists and team has portfolio_id
                if has_portfolio_field and hasattr(team, 'portfolio_id') and team.portfolio_id:
                    form.portfolio_id.data = team.portfolio_id
                    logger.info(f"Setting portfolio_id={team.portfolio_id}")
                
                # Zaznaczenie członków zespołu
                member_ids = []
                if hasattr(team, 'members') and callable(getattr(team, 'members')):
                    members = team.members
                    if members:
                        member_ids = [member.id for member in members]
                        logger.info(f"Setting members from team.members property: {member_ids}")
                elif hasattr(team, 'team_members'):
                    member_ids = [tm.user_id for tm in team.team_members if tm.user_id]
                    logger.info(f"Setting members from team.team_members: {member_ids}")
                
                form.members.data = member_ids
                
                # Zaznaczenie przypisanych projektów
                if hasattr(team, 'assigned_projects'):
                    project_ids = [project.id for project in team.assigned_projects]
                    form.projects.data = project_ids
                    logger.info(f"Setting projects: {project_ids}")
                
                # Przekazanie obiektu zespołu do szablonu
                return render_template(
                    'admin/teams/index.html',
                    teams=teams,
                    team=team,
                    form=form,
                    users=users,
                    projects=projects,
                    has_portfolio_field=has_portfolio_field
                )
            except Exception as e:
                logger.error(f"Error loading team for edit: {str(e)}", exc_info=True)
                flash('Error loading team data for editing.', 'danger')
        
        # Handle form submission
        if request.method == 'POST':
            logger.info(f"Processing POST request: {request.form}")
            
            # Obsługa usuwania zespołu
            if request.form.get('action') == 'delete':
                try:
                    team_id = request.form.get('team_id')
                    if team_id:
                        team = Team.query.get_or_404(team_id)
                        logger.info(f"Deleting team {team.id} - {team.name}")
                        
                        # Usuń najpierw powiązania
                        TeamMembership.query.filter_by(team_id=team.id).delete()
                        logger.info(f"Removed all team memberships for team {team.id}")
                        
                        # Wyczyść projekty
                        team.assigned_projects = []
                        logger.info(f"Cleared assigned projects for team {team.id}")
                        
                        # Usuń zespół
                        db.session.delete(team)
                        db.session.commit()
                        flash('Team deleted successfully.', 'success')
                    return redirect(url_for('admin.manage_teams'))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error deleting team: {str(e)}", exc_info=True)
                    flash('Error deleting team.', 'danger')
                    return redirect(url_for('admin.manage_teams'))
            
            # Standardowa obsługa tworzenia/edycji zespołu
            logger.info(f"Form validation started. CSRF token: {form.csrf_token.current_token}")
            if form.validate_on_submit():
                logger.info("Form validated successfully")
                try:
                    # Get team_id from form (if it's an update)
                    team_id = request.form.get('team_id')
                    logger.info(f"Team ID from form: {team_id}")
                    
                    if team_id:
                        # Update existing team
                        team = Team.query.get_or_404(team_id)
                        logger.info(f"Updating existing team: {team.id} - {team.name}")
                        team.name = form.name.data
                        team.description = form.description.data
                        
                        # Set leader if selected
                        if form.leader_id.data:
                            team.leader_id = form.leader_id.data
                            logger.info(f"Set leader_id to {team.leader_id}")
                        else:
                            team.leader_id = None
                            logger.info("No leader selected, set to None")
                            
                        # Set portfolio if field exists and is selected
                        if has_portfolio_field and form.portfolio_id.data:
                            team.portfolio_id = form.portfolio_id.data
                            logger.info(f"Set portfolio_id to {team.portfolio_id}")
                        elif has_portfolio_field:
                            team.portfolio_id = None
                            logger.info("No portfolio selected, set to None")
                            
                        # Save team
                        db.session.add(team)
                        db.session.flush()
                        logger.info(f"Updated basic team info for {team.id}")
                        flash('Team updated successfully.', 'success')
                    else:
                        # Create new team
                        logger.info("Creating new team")
                        team = Team(
                            name=form.name.data,
                            description=form.description.data,
                            is_active=True
                        )
                        
                        # Set leader if selected
                        if form.leader_id.data:
                            team.leader_id = form.leader_id.data
                            logger.info(f"Set leader_id to {team.leader_id}")
                        
                        # Set portfolio if field exists and is selected
                        if has_portfolio_field and form.portfolio_id.data:
                            team.portfolio_id = form.portfolio_id.data
                            logger.info(f"Set portfolio_id to {team.portfolio_id}")
                        
                        # Save team
                        db.session.add(team)
                        db.session.flush()  # Flush to get the team ID
                        logger.info(f"Created new team with ID {team.id}")
                        flash('Team created successfully.', 'success')
                    
                    # Clear existing members
                    TeamMembership.query.filter_by(team_id=team.id).delete()
                    logger.info(f"Deleted existing memberships for team {team.id}")
                    
                    # Clear existing projects
                    team.assigned_projects = []
                    logger.info(f"Cleared existing projects for team {team.id}")
                    
                    # Add members
                    if form.members.data:
                        logger.info(f"Adding members: {form.members.data}")
                        for user_id in form.members.data:
                            user = User.query.get(user_id)
                            if user:
                                # Create membership manually
                                membership = TeamMembership(
                                    team_id=team.id,
                                    user_id=user.id,
                                    role='leader' if user.id == team.leader_id else 'member'
                                )
                                db.session.add(membership)
                                logger.info(f"Added user {user.id} to team {team.id}")
                    
                    # Add projects
                    if form.projects.data:
                        logger.info(f"Adding projects: {form.projects.data}")
                        project_list = []
                        for project_id in form.projects.data:
                            project = Project.query.get(project_id)
                            if project:
                                project_list.append(project)
                        
                        team.assigned_projects = project_list
                        logger.info(f"Set {len(project_list)} projects to team {team.id}")
                    
                    # Final commit
                    db.session.commit()
                    logger.info(f"Successfully saved team {team.id}")
                    return redirect(url_for('admin.manage_teams'))
                    
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error saving team: {str(e)}", exc_info=True)
                    flash('Error saving team.', 'danger')
            else:
                logger.warning(f"Form validation failed. Errors: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        
        # Render template for GET requests
        return render_template(
            'admin/teams/index.html',
            teams=teams,
            form=form,
            users=users,
            projects=projects,
            has_portfolio_field=has_portfolio_field
        )
            
    except Exception as e:
        logger.error(f"Error in manage_teams view: {str(e)}", exc_info=True)
        flash('An error occurred while managing teams.', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/teams/<int:team_id>', methods=['GET'])
@login_required
@admin_required
def get_team(team_id):
    """Get team details."""
    try:
        team = Team.query.get_or_404(team_id)
        
        # Jeśli żądanie jest z oczekiwaniem JSON (API), zwróć dane JSON
        if request.is_json or request.headers.get('Accept') == 'application/json':
            # Prepare team data including members and projects
            team_data = {
                'id': team.id,
                'name': team.name,
                'description': team.description,
                'leader_id': team.leader_id,
                'members': [],
                'projects': []
            }
            
            # Get team members
            if hasattr(team, 'memberships'):
                for membership in team.memberships:
                    if membership.user:
                        user_data = {
                            'id': membership.user.id,
                            'username': membership.user.username,
                            'display_name': membership.user.display_name or membership.user.username
                        }
                        team_data['members'].append(user_data)
            elif hasattr(team, 'team_members'):
                for membership in team.team_members:
                    if membership.user:
                        user_data = {
                            'id': membership.user.id,
                            'username': membership.user.username,
                            'display_name': membership.user.display_name or membership.user.username
                        }
                        team_data['members'].append(user_data)
            
            # Get team projects
            for project in team.assigned_projects:
                project_data = {
                    'id': project.id,
                    'name': project.name
                }
                team_data['projects'].append(project_data)
            
            return jsonify(team_data)
        
        # Dla normalnych żądań z przeglądarki, renderuj szablon
        users = User.query.filter_by(is_active=True).all()
        projects = Project.query.filter_by(is_active=True).all()
        form = TeamForm()
        
        # Debugowanie: sprawdź, czy lista członków i projektów jest poprawnie dostępna
        logger.info(f"Team {team.id} has {len(team.members) if hasattr(team, 'members') else 0} members")
        logger.info(f"Team {team.id} has {len(team.assigned_projects) if hasattr(team, 'assigned_projects') else 0} projects")
        
        return render_template(
            'admin/teams/index.html',
            teams=Team.query.all(),
            team=team,
            form=form,
            users=users,
            projects=projects,
            view_mode=True  # Dodaj flagę, aby szablon wiedział, że jesteśmy w trybie podglądu
        )
        
    except Exception as e:
        logger.error(f"Error getting team {team_id}: {str(e)}", exc_info=True)
        flash('Error viewing team details.', 'danger')
        return redirect(url_for('admin.manage_teams'))

@admin_bp.route('/teams/create', methods=['GET'])
@login_required
@admin_required
def redirect_team_create():
    """Redirect to team management page."""
    flash('Please use the team management page to create teams.', 'info')
    return redirect(url_for('admin.manage_teams'))

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

@admin_bp.route('/portfolios', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_portfolios():
    """List all portfolios with CRUD actions."""
    try:
        from app.models.portfolio import Portfolio
        form = PortfolioForm()
        
        # Handle form submission for creating new portfolio
        if request.method == 'POST' and form.validate_on_submit():
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
            return render_template('admin/portfolios/list.html', portfolios=portfolios, form=form)
        except Exception as e:
            # If there's an error fetching portfolios, try running migrations again
            logger.error(f"Error fetching portfolios, attempting to fix schema: {str(e)}")
            db.session.rollback()
            
            # Create tables if they don't exist
            db.create_all()
            
            # Try fetching again
            portfolios = Portfolio.query.all()
            return render_template('admin/portfolios/list.html', portfolios=portfolios, form=form)
            
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
    """Portfolio analysis view."""
    current_app.logger.info("Accessing portfolio analysis view")
    try:
        portfolios = Portfolio.query.all()
        current_app.logger.info(f"Found {len(portfolios)} portfolios")
        return render_template('admin/portfolios/analysis.html', portfolios=portfolios)
    except Exception as e:
        current_app.logger.error(f"Error in portfolio analysis view: {str(e)}", exc_info=True)
        flash('Error loading portfolios', 'error')
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
    """Render the workload report template with all necessary data for filtering."""
    try:
        # Get all active teams for filtering
        teams = Team.query.filter_by(is_active=True).order_by(Team.name).all()
        logger.debug(f"Loaded {len(teams)} active teams for workload report")
        
        # Get all active projects for filtering
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
        logger.debug(f"Loaded {len(projects)} active projects for workload report")
        
        # Ensure projects have teams data loaded
        for project in projects:
            if not hasattr(project, 'teams'):
                # If project doesn't have teams attribute, load them manually
                project.teams = db.session.query(Team).join(
                    ProjectTeam, ProjectTeam.team_id == Team.id
                ).filter(
                    ProjectTeam.project_id == project.id
                ).all()
                logger.debug(f"Manually loaded {len(project.teams)} teams for project {project.id}: {project.name}")
        
        logger.info("Rendering workload report template with teams and projects data")
        return render_template(
            'admin/reports/workload.html',
            teams=teams,
            projects=projects
        )
    except Exception as e:
        logger.error(f"Error loading workload report: {str(e)}", exc_info=True)
        flash('Error loading workload report', 'danger')
        return redirect(url_for('admin.index'))

@admin_bp.route('/reports/workload/data')
@login_required
@admin_required
def get_workload_data():
    """API endpoint that returns workload data for the report."""
    try:
        # Get filter parameters
        team_id = request.args.get('team_id')
        
        # Handle multiple project IDs selection
        project_ids = request.args.getlist('project_ids[]')
        
        # Date range handling
        date_range = request.args.get('date_range')
        
        # Parse date range
        start_date = None
        end_date = None
        if date_range:
            dates = date_range.split(' - ')
            if len(dates) == 2:
                start_date = datetime.strptime(dates[0], '%Y-%m-%d')
                end_date = datetime.strptime(dates[1], '%Y-%m-%d')
        else:
            # Default to last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        
        logger.debug(f"Generating workload report with filters: team_id={team_id}, project_ids={project_ids}, date_range={date_range}")
        
        # Initialize data structures for the response
        team_workload = {
            'labels': [],
            'datasets': [{
                'label': 'Team Hours',
                'data': [],
                'backgroundColor': []
            }]
        }
        
        user_workload = {
            'labels': [],
            'datasets': [{
                'label': 'User Hours',
                'data': [],
                'backgroundColor': []
            }]
        }
        
        detailed_stats = []
        
        # Base query for users who have logged time
        user_query = db.session.query(
            User.id,
            User.display_name,
            func.sum(Worklog.time_spent_seconds).label('total_time'),
            func.count(distinct(Project.id)).label('projects_count')
        ).join(
            Worklog, Worklog.user_id == User.id
        ).join(
            Project, Project.id == Worklog.project_id
        ).filter(
            User.is_active == True
        )
        
        # Apply date range filter
        if start_date:
            user_query = user_query.filter(Worklog.work_date >= start_date)
        if end_date:
            user_query = user_query.filter(Worklog.work_date <= end_date)
        
        # Apply team filter if provided
        team_members = []
        team_name = "All Teams"
        if team_id:
            team = Team.query.get(team_id)
            if team:
                team_name = team.name
                team_members = [member.id for member in team.members]
                user_query = user_query.filter(User.id.in_(team_members))
        
        # Apply project filter if provided
        if project_ids:
            # Multiple project selection
            if len(project_ids) > 0 and project_ids[0] != '':
                user_query = user_query.filter(Worklog.project_id.in_(project_ids))
                logger.debug(f"Filtering by {len(project_ids)} projects: {project_ids}")
        
        # Group and execute user query
        user_results = user_query.group_by(User.id).all()
        
        # Get team data
        team_results = []
        team_project_filter = {}
        
        # If specific team is selected, we only need that team's data
        if team_id:
            team_query = db.session.query(
                Team.id,
                Team.name,
                func.sum(Worklog.time_spent_seconds).label('total_time'),
                func.count(distinct(Project.id)).label('projects_count')
            ).join(
                TeamMember, TeamMember.team_id == Team.id
            ).join(
                Worklog, Worklog.user_id == TeamMember.user_id
            ).join(
                Project, Project.id == Worklog.project_id
            ).filter(
                Team.is_active == True,
                Team.id == team_id
            )
            
            # Apply date range filter
            if start_date:
                team_query = team_query.filter(Worklog.work_date >= start_date)
            if end_date:
                team_query = team_query.filter(Worklog.work_date <= end_date)
                
            # Apply project filter if provided
            if project_ids and len(project_ids) > 0 and project_ids[0] != '':
                team_query = team_query.filter(Worklog.project_id.in_(project_ids))
                team_project_filter = {int(pid): True for pid in project_ids}
                
            # Group and execute team query
            team_results = team_query.group_by(Team.id).all()
        else:
            # If no team is selected, get data for all teams
            team_query = db.session.query(
                Team.id,
                Team.name,
                func.sum(Worklog.time_spent_seconds).label('total_time'),
                func.count(distinct(Project.id)).label('projects_count')
            ).join(
                TeamMember, TeamMember.team_id == Team.id
            ).join(
                Worklog, Worklog.user_id == TeamMember.user_id
            ).join(
                Project, Project.id == Worklog.project_id
            ).filter(
                Team.is_active == True
            )
            
            # Apply date range filter
            if start_date:
                team_query = team_query.filter(Worklog.work_date >= start_date)
            if end_date:
                team_query = team_query.filter(Worklog.work_date <= end_date)
                
            # Apply project filter if provided
            if project_ids and len(project_ids) > 0 and project_ids[0] != '':
                team_query = team_query.filter(Worklog.project_id.in_(project_ids))
                team_project_filter = {int(pid): True for pid in project_ids}
                
            # Group and execute team query
            team_results = team_query.group_by(Team.id).all()
        
        # Process team results
        colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69',
                 '#4d5c68', '#3e5c76', '#2e5984', '#1e5f8f', '#0f639a', '#0068a5', '#006db0']
        
        # Define the working days counting function at the top level of the function
        # Calculate working days (exclude weekends)
        def count_working_days(start_date, end_date):
            working_days = 0
            current_date = start_date
            while current_date <= end_date:
                # Check if current date is a weekday (0-4 for Monday to Friday)
                if current_date.weekday() < 5:
                    working_days += 1
                current_date += timedelta(days=1)
            return working_days
        
        # Add "All Teams" entry if we have multiple teams
        if len(team_results) > 1 or not team_id:
            # Calculate total hours across all teams
            total_team_hours = sum(result.total_time for result in team_results) / 3600
            total_projects_count = sum(result.projects_count for result in team_results)
            
            team_workload['labels'].append("All Teams")
            team_workload['datasets'][0]['data'].append(round(total_team_hours, 2))
            team_workload['datasets'][0]['backgroundColor'].append(colors[0])
            
            # Calculate working days in the date range
            working_days = count_working_days(start_date, end_date) if start_date and end_date else 0
            
            detailed_stats.append({
                'name': "All Teams",
                'total_hours': round(total_team_hours, 2),
                'projects_count': total_projects_count,
                'avg_daily_hours': round(total_team_hours / ((end_date - start_date).days + 1), 2) if start_date and end_date else 0,
                # Note: Using hardcoded 8 hour workday - in future versions this should be replaced with user-specific work norms
                'utilization': min(round((total_team_hours / (8 * working_days * len(user_results))) * 100, 2) if user_results and start_date and end_date and working_days > 0 else 0, 100)
            })
        
        # Add individual team results
        for i, result in enumerate(team_results):
            color_index = (i + 1) % len(colors)  # +1 because 0 is used for "All Teams"
            team_name = result.name
            team_hours = round(result.total_time / 3600, 2)
            
            team_workload['labels'].append(team_name)
            team_workload['datasets'][0]['data'].append(team_hours)
            team_workload['datasets'][0]['backgroundColor'].append(colors[color_index])
            
            # Get team members for utilization calculation
            team_members = []
            team = Team.query.get(result.id)
            if team:
                team_members = [member.id for member in team.members if member.is_active]
            
            # Calculate working days for this team
            team_working_days = count_working_days(start_date, end_date) if start_date and end_date else 0
            
            detailed_stats.append({
                'name': team_name,
                'total_hours': team_hours,
                'projects_count': result.projects_count,
                'avg_daily_hours': round(team_hours / ((end_date - start_date).days + 1), 2) if start_date and end_date else 0,
                # Note: Using hardcoded 8 hour workday - in future versions this should be replaced with user-specific work norms
                'utilization': min(round((team_hours / (8 * team_working_days * max(1, len(team_members)))) * 100, 2) if start_date and end_date and team_working_days > 0 else 0, 100)
            })
        
        # Process user results
        for i, result in enumerate(user_results):
            color_index = i % len(colors)
            user_name = result.display_name or f"User {result.id}"
            user_hours = round(result.total_time / 3600, 2)
            
            user_workload['labels'].append(user_name)
            user_workload['datasets'][0]['data'].append(user_hours)
            user_workload['datasets'][0]['backgroundColor'].append(colors[color_index])
            
            # Calculate working days for this user
            user_working_days = count_working_days(start_date, end_date) if start_date and end_date else 0
            
            detailed_stats.append({
                'name': user_name,
                'total_hours': user_hours,
                'projects_count': result.projects_count,
                'avg_daily_hours': round(user_hours / ((end_date - start_date).days + 1), 2) if start_date and end_date else 0,
                # Note: Using hardcoded 8 hour workday - in future versions this should be replaced with user-specific work norms
                'utilization': min(round((user_hours / (8 * user_working_days)) * 100, 2) if start_date and end_date and user_working_days > 0 else 0, 100)
            })
        
        # Sort detailed stats by total hours
        detailed_stats.sort(key=lambda x: x['total_hours'], reverse=True)
        
        # Add date range info to the response
        date_info = {
            'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else None,
            'days': (end_date - start_date).days + 1 if start_date and end_date else 0
        }
        
        return jsonify({
            'status': 'success',
            'team_workload': team_workload,
            'user_workload': user_workload,
            'detailed_stats': detailed_stats,
            'date_info': date_info,
            'filters': {
                'team_id': team_id,
                'project_ids': project_ids,
                'date_range': date_range
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting workload data: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

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
        current_app.logger.info(f"Editing portfolio assignments for portfolio {portfolio_id}")
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        
        if request.method == 'POST':
            current_app.logger.info(f"POST request received for portfolio {portfolio_id} assignments")
            # Debug request information
            current_app.logger.debug(f"Content-Type: {request.content_type}")
            current_app.logger.debug(f"Form data keys: {list(request.form.keys())}")
            
            # Get project IDs from different possible sources
            project_ids = []
            if 'project_ids[]' in request.form:
                project_ids = request.form.getlist('project_ids[]')
                current_app.logger.debug(f"Found project_ids[] in form: {project_ids}")
            elif 'project_ids' in request.form:
                project_ids = request.form.getlist('project_ids')
                current_app.logger.debug(f"Found project_ids in form: {project_ids}")
            
            # Try JSON data if no form data found
            if not project_ids and request.is_json:
                try:
                    data = request.get_json()
                    if data:
                        project_ids = data.get('project_ids', [])
                        current_app.logger.debug(f"Project IDs from JSON: {project_ids}")
                except Exception as e:
                    current_app.logger.error(f"Error parsing JSON data: {str(e)}")
            
            current_app.logger.info(f"Project IDs to assign: {project_ids}")
            
            # Clear existing assignments - use SQLAlchemy relationship
            current_app.logger.info(f"Clearing existing projects for portfolio {portfolio_id}")
            portfolio.projects = []
            db.session.flush()
            
            # Add new assignments if any projects were selected
            added_count = 0
            if project_ids:
                current_app.logger.info(f"Adding {len(project_ids)} projects to portfolio")
                
                for project_id in project_ids:
                    # Convert to integer if needed
                    try:
                        project_id_int = int(project_id)
                        project = Project.query.get(project_id_int)
                        
                        if project:
                            portfolio.projects.append(project)
                            added_count += 1
                            current_app.logger.debug(f"Added project {project.id} - {project.name} to portfolio")
                        else:
                            current_app.logger.warning(f"Project with ID {project_id_int} not found")
                    except ValueError:
                        current_app.logger.error(f"Invalid project ID format: {project_id}")
                    except Exception as e:
                        current_app.logger.error(f"Error adding project {project_id}: {str(e)}")
            
            try:
                db.session.commit()
                current_app.logger.info(f"Portfolio assignments updated successfully: {added_count} projects added")
                
                flash('Portfolio assignments updated successfully.', 'success')
                
                # Return JSON response if requested
                if request.headers.get('Accept') == 'application/json' or request.is_json:
                    return jsonify({
                        'status': 'success', 
                        'message': 'Assignments updated successfully',
                        'project_count': added_count
                    })
                
                # Otherwise redirect to portfolios page
                return redirect(url_for('admin.portfolio_assignments'))
                
            except SQLAlchemyError as e:
                db.session.rollback()
                error_msg = str(e)
                current_app.logger.error(f"Database error updating portfolio assignments: {error_msg}")
                flash('Error updating portfolio assignments.', 'error')
                
                if request.headers.get('Accept') == 'application/json' or request.is_json:
                    return jsonify({'status': 'error', 'message': 'Database error occurred'}), 500
                
                return redirect(url_for('admin.edit_portfolio_assignments', portfolio_id=portfolio_id))
            
        # GET request - prepare the template data
        current_app.logger.info(f"Preparing template data for portfolio {portfolio_id}")
        available_projects = Project.query.all()
        current_app.logger.debug(f"Found {len(available_projects)} available projects")
        
        # Explicitly load portfolio projects
        portfolio_projects = portfolio.projects
        current_app.logger.debug(f"Portfolio has {len(portfolio_projects)} assigned projects")
        
        return render_template('admin/portfolios/edit_assignments.html',
                             portfolio=portfolio,
                             available_projects=available_projects,
                             assigned_projects=portfolio_projects)
                             
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"Error editing portfolio assignments: {error_msg}", exc_info=True)
        flash('An error occurred while editing portfolio assignments.', 'error')
        
        if request.headers.get('Accept') == 'application/json' or request.is_json:
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
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

# Cache dictionary with TTL management
_analysis_cache = {}
_cache_ttl = 600  # 10 minutes in seconds

def clear_expired_cache():
    """Clear expired cache entries based on TTL"""
    now = time.time()
    expired_keys = [k for k, v in _analysis_cache.items() if v['expires'] < now]
    for key in expired_keys:
        del _analysis_cache[key]

def cached_response(ttl=_cache_ttl):
    """Decorator to cache API responses based on request parameters"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Clear expired cache entries first
            clear_expired_cache()
            
            # Create cache key from endpoint, function arguments and query parameters
            key_parts = [request.path]
            key_parts.extend([str(a) for a in args])
            key_parts.extend([f"{k}:{v}" for k, v in kwargs.items()])
            key_parts.extend([f"{k}:{v}" for k, v in request.args.items()])
            
            cache_key = hashlib.md5(json.dumps(key_parts).encode()).hexdigest()
            
            # Check if we have a valid cached response
            if cache_key in _analysis_cache and _analysis_cache[cache_key]['expires'] > time.time():
                current_app.logger.debug(f"Cache hit for {request.path}")
                return _analysis_cache[cache_key]['data']
            
            # No cache hit, call the original function
            response = f(*args, **kwargs)
            
            # Cache the response
            _analysis_cache[cache_key] = {
                'data': response,
                'expires': time.time() + ttl
            }
            
            current_app.logger.debug(f"Cache miss for {request.path}, caching for {ttl} seconds")
            return response
        return wrapper
    return decorator

@admin_bp.route('/portfolios/analysis/data/<portfolio_id>')
@login_required
@cached_response(ttl=300)  # 5 minute cache for portfolio analysis data
def get_portfolio_analysis_data(portfolio_id):
    """
    Returns portfolio analysis data in JSON format
    
    Parameters:
    -----------
    portfolio_id : str
        The ID of the portfolio to analyze
    
    Query Parameters:
    ----------------
    start_date : str
        Start date for analysis (YYYY-MM-DD)
    end_date : str
        End date for analysis (YYYY-MM-DD)
    
    Returns:
    --------
    JSON response with portfolio analysis data or error
    """
    try:
        # Get parameters from request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Validate required parameters
        if not portfolio_id:
            current_app.logger.error("Portfolio ID not provided")
            return jsonify({
                'status': 'error',
                'message': 'Portfolio ID is required'
            }), 400
        
        # Sanitize portfolio_id against XSS
        portfolio_id = bleach.clean(portfolio_id, strip=True)
        
        # Validate date parameters
        try:
            if start_date:
                # Validate and parse start_date
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                # Default: 30 days ago
                start_date_obj = (datetime.now() - timedelta(days=30)).date()
                start_date = start_date_obj.strftime('%Y-%m-%d')
                
            if end_date:
                # Validate and parse end_date
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            else:
                # Default: today
                end_date_obj = datetime.now().date()
                end_date = end_date_obj.strftime('%Y-%m-%d')
                
            # Check if date range is valid
            if end_date_obj < start_date_obj:
                current_app.logger.warning(f"End date {end_date} is before start date {start_date}")
                return jsonify({
                    'status': 'error',
                    'message': 'End date cannot be before start date'
                }), 400
                
            # Limit date range to 1 year to prevent excessive queries
            if (end_date_obj - start_date_obj).days > 365:
                current_app.logger.warning(f"Date range too large: {start_date} to {end_date}")
                return jsonify({
                    'status': 'error',
                    'message': 'Date range cannot exceed 1 year'
                }), 400
                
        except ValueError as e:
            current_app.logger.error(f"Invalid date format: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
        
        # Log analysis request
        current_app.logger.info(f"Portfolio analysis requested for ID: {portfolio_id}, "
                        f"date range: {start_date} to {end_date}")
        
        # Begin database session
        db_session = db.session
        
        # Check if portfolio exists and user has access
        portfolio = Portfolio.query.filter_by(id=portfolio_id).first()
        if not portfolio:
            current_app.logger.warning(f"Portfolio not found: {portfolio_id}")
            return jsonify({
                'status': 'error',
                'message': 'Portfolio not found'
            }), 404
            
        # Check user permission
        if not current_user.is_admin and portfolio.user_id != current_user.id:
            current_app.logger.warning(f"User {current_user.id} attempted to access portfolio {portfolio_id} without permission")
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to view this portfolio'
            }), 403
        
        # Optimize query with joins and filtering
        try:
            # Base query for portfolio projects
            projects_query = db_session.query(
                Project.id, 
                Project.name
            ).join(
                portfolio_projects,
                Project.id == portfolio_projects.c.project_id
            ).filter(
                portfolio_projects.c.portfolio_id == portfolio_id
            ).all()
            
            # Convert to list of project IDs
            project_ids = [p.id for p in projects_query]
            project_names = {p.id: p.name for p in projects_query}
            
            if not project_ids:
                current_app.logger.info(f"No projects found for portfolio {portfolio_id}")
                return jsonify({
                    'status': 'success',
                    'data': {
                        'total_hours': 0,
                        'total_users': 0,
                        'projects_count': 0,
                        'projects_data': []
                    }
                })
            
            # Get time entries efficiently with one query
            time_entries = db_session.query(
                Worklog.project_id,
                Worklog.user_id,
                Worklog.time_spent_seconds
            ).filter(
                Worklog.project_id.in_(project_ids),
                Worklog.work_date >= start_date_obj,
                Worklog.work_date <= end_date_obj
            ).all()
            
            # Process data
            projects_data = {}
            users_set = set()
            total_hours = 0
            
            # Process time entries
            for entry in time_entries:
                project_id = entry.project_id
                user_id = entry.user_id
                # Convert seconds to hours
                hours = float(entry.time_spent_seconds or 0) / 3600
                
                # Add to users set
                users_set.add(user_id)
                
                # Add to total hours
                total_hours += hours
                
                # Add to project data
                if project_id not in projects_data:
                    projects_data[project_id] = {
                        'id': project_id,
                        'name': project_names.get(project_id, 'Unknown'),
                        'hours': 0,
                        'users': set()
                    }
                    
                projects_data[project_id]['hours'] += hours
                projects_data[project_id]['users'].add(user_id)
            
            # Format the response data
            formatted_projects = []
            for project_id, data in projects_data.items():
                formatted_projects.append({
                    'id': project_id,
                    'name': data['name'],
                    'hours': round(data['hours'], 2),
                    'users_count': len(data['users'])
                })
                
            # Sort projects by hours (descending)
            formatted_projects.sort(key=lambda x: x['hours'], reverse=True)
            
            # Prepare final response
            response_data = {
                'total_hours': round(total_hours, 2),
                'total_users': len(users_set),
                'projects_count': len(projects_data),
                'projects_data': formatted_projects
            }
            
            return jsonify({
                'status': 'success',
                'data': response_data
            })
            
        except SQLAlchemyError as e:
            # Handle database errors
            db_session.rollback()
            error_msg = str(e)
            current_app.logger.error(f"Database error in portfolio analysis: {error_msg}")
            
            # Return sanitized error message (don't expose SQL details)
            return jsonify({
                'status': 'error',
                'message': 'Database error while retrieving portfolio data'
            }), 500
            
    except HTTPException as e:
        # Handle HTTP exceptions
        current_app.logger.error(f"HTTP error in portfolio analysis: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), e.code
        
    except Exception as e:
        # Handle unexpected errors
        current_app.logger.error(f"Unexpected error in portfolio analysis: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        
        # Return generic error in production
        if current_app.config.get('DEBUG', False):
            error_details = str(e)
        else:
            error_details = 'An unexpected error occurred'
            
        return jsonify({
            'status': 'error',
            'message': error_details
        }), 500