from flask import Blueprint, render_template, g, redirect, url_for, flash, session, request, send_from_directory, jsonify, current_app, send_file, make_response
from app.utils.decorators import auth_required, admin_required
from pathlib import Path
from app.services.jira_service import get_jira_service, test_connection, save_jira_config
from app.services.dashboard_service import get_dashboard_stats
import logging
from datetime import datetime, timedelta
import os
from app.services.admin_service import (
    get_users_count, get_active_users_count, get_total_worklogs, 
    get_total_projects, is_jira_connected, get_last_sync_time, 
    get_system_status, get_system_logs, save_app_settings
)
from flask_wtf import FlaskForm
from typing import Dict, Any
from flask_login import current_user, login_required
from app.models import User, Project, Worklog, Setting, ProjectAssignment, Team, Role
from app.middleware import log_errors
from app.middleware.access_control import check_project_access, check_team_access
from app.forms.admin import (
    UserForm, JiraSettingsForm, SystemSettingsForm, SettingsForm, JiraConfigForm, ProjectForm
)
from app.forms import UserSettingsForm
from app.models.user_role import UserRole
from app.extensions import db
import json
from app.models.jira_config import JiraConfig
from flask_wtf.csrf import generate_csrf
from app.models.user import User
from app.services.jira_service import JiraService
import io
import xlsxwriter
from app.models.issue import Issue
from sqlalchemy import func, distinct

views_bp = Blueprint('views', __name__, url_prefix='/views')
logger = logging.getLogger(__name__)

@views_bp.route('/tasks')
@login_required
def tasks():
    """Lista zadań."""
    try:
        logger.info(f"Loading tasks for user: {current_user.username}")
        
        jira_service = JiraService()
        if not jira_service.is_connected:
            logger.error("JIRA service not connected")
            raise Exception("Nie można połączyć się z JIRA")

        # Pobierz zadania dla zalogowanego użytkownika
        username = current_user.username
        jql = f'assignee = "{username}" AND status not in (Closed, Resolved) ORDER BY updated DESC'
        logger.info(f"Executing JQL: {jql}")
        
        tasks = jira_service.jira.search_issues(jql, maxResults=50)
        logger.info(f"Found {len(tasks) if tasks else 0} tasks")
        
        return render_template('tasks.html', 
                             tasks=tasks if tasks else [], 
                             user=current_user,
                             jira_url=jira_service.server)  # Dodaj URL JIRA
    except Exception as e:
        logger.error(f"Error loading tasks: {str(e)}")
        flash('Wystąpił błąd podczas ładowania zadań.', 'danger')
        return render_template('tasks.html', 
                             tasks=[], 
                             user=current_user,
                             jira_url=None)

@views_bp.route('/projects')
@login_required
def projects():
    """Lista projektów."""
    try:
        jira_service = JiraService()
        if not jira_service.is_connected:
            raise Exception("Nie można połączyć się z JIRA")

        projects = jira_service.get_projects()
        return render_template('projects.html', 
                             projects=projects,
                             jira_url=jira_service.server)
    except Exception as e:
        logger.error(f"Error loading projects: {str(e)}")
        flash('Wystąpił błąd podczas ładowania projektów.', 'danger')
        return render_template('projects.html', 
                             projects=[],
                             jira_url=None)

@views_bp.route('/project/<string:project_key>')
@login_required
def project(project_key):
    """Widok szczegółów projektu."""
    try:
        project = Project.query.filter_by(jira_key=project_key).first_or_404()
        return render_template('project/details.html', project=project)
    except Exception as e:
        logger.error(f"Error loading project details: {str(e)}", exc_info=True)
        flash('Wystąpił błąd podczas ładowania szczegółów projektu', 'error')
        return redirect(url_for('views.projects'))

@views_bp.route('/worklog')
@login_required
def worklog():
    """Widok worklogów z lokalnej bazy danych."""
    try:
        # Pobierz parametry filtrowania
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        project_key = request.args.get('project', None)
        user_id = request.args.get('user_id', None)

        # Jeśli nie podano dat, ustaw ostatni tydzień jako domyślny zakres
        if not start_date:
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')

        # Podstawowe zapytanie
        query = Worklog.query\
            .join(Worklog.user)\
            .join(Worklog.project)\
            .join(Worklog.issue)

        # Dodaj filtry
        if start_date:
            query = query.filter(Worklog.work_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Worklog.work_date <= datetime.strptime(end_date, '%Y-%m-%d'))
        if project_key:
            query = query.filter(Project.jira_key == project_key)
        if user_id:
            query = query.filter(Worklog.user_id == user_id)
        else:
            # Jeśli nie jest adminem, pokaż tylko jego worklogi
            if not current_user.is_admin:
                query = query.filter(Worklog.user_id == current_user.id)

        # Sortowanie
        query = query.order_by(Worklog.work_date.desc())

        # Pobierz worklogi
        worklogs = query.all()
        logger.info(f"Found {len(worklogs)} worklogs")

        # Przygotuj dane do widoku
        worklog_data = []
        for worklog in worklogs:
            worklog_data.append({
                'id': worklog.id,
                'user': {
                    'id': worklog.user.id,
                    'name': worklog.user.display_name or worklog.user.username,
                    'email': worklog.user.email
                },
                'project': {
                    'key': worklog.project.jira_key,
                    'name': worklog.project.name
                },
                'issue': {
                    'key': worklog.issue.jira_key,
                    'summary': worklog.issue.summary
                },
                'time_spent_seconds': worklog.time_spent_seconds,
                'time_spent_hours': round(worklog.time_spent_seconds / 3600, 2),
                'work_date': worklog.work_date.strftime('%Y-%m-%d %H:%M'),
                'created': worklog.created_at.strftime('%Y-%m-%d %H:%M'),
                'updated': worklog.updated_at.strftime('%Y-%m-%d %H:%M') if worklog.updated_at else None
            })

        # Pobierz projekty do filtra
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
        project_choices = [{'key': p.jira_key, 'name': p.name} for p in projects]

        # Pobierz użytkowników do filtra (tylko dla adminów)
        users = []
        if current_user.is_admin:
            users = User.query.filter_by(is_active=True).order_by(User.display_name).all()
            users = [{'id': u.id, 'name': u.display_name or u.username} for u in users]

        return render_template('worklog/index.html',
                            worklogs=worklog_data,
                            projects=project_choices,
                            users=users,
                            filters={
                                'start_date': start_date,
                                'end_date': end_date,
                                'project': project_key,
                                'user_id': user_id
                            })

    except Exception as e:
        logger.error(f"Error in worklog view: {str(e)}")
        flash('Error loading worklogs', 'error')
        return redirect(url_for('views.index'))

@views_bp.route('/reports')
@login_required
def reports():
    """Lista raportów."""
    return render_template('reports.html')

@views_bp.route('/reports/worklog')
@login_required
def worklog_report():
    """Raport czasu pracy z bazy danych."""
    try:
        # Pobierz parametry filtrowania
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        project_key = request.args.get('project', None)
        user_id = request.args.get('user_id', None)

        # Domyślny zakres dat (ostatni miesiąc)
        if not start_date:
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')

        # Podstawowe zapytanie
        query = db.session.query(
            User.display_name.label('user_name'),
            Project.name.label('project_name'),
            Project.jira_key.label('project_key'),
            func.sum(Worklog.time_spent_seconds).label('total_time'),
            func.count(Worklog.id).label('worklog_count')
        ).join(Worklog.user)\
         .join(Worklog.project)\
         .group_by(User.id, Project.id)

        # Dodaj filtry
        if start_date:
            query = query.filter(Worklog.work_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Worklog.work_date <= datetime.strptime(end_date, '%Y-%m-%d'))
        if project_key:
            query = query.filter(Project.jira_key == project_key)
        if user_id:
            query = query.filter(Worklog.user_id == user_id)
        elif not current_user.is_admin:
            # Jeśli nie jest adminem, pokaż tylko jego worklogi
            query = query.filter(Worklog.user_id == current_user.id)

        results = query.all()

        # Przygotuj dane do raportu
        report_data = []
        for result in results:
            report_data.append({
                'user_name': result.user_name,
                'project_name': result.project_name,
                'project_key': result.project_key,
                'total_hours': round(result.total_time / 3600, 2),
                'worklog_count': result.worklog_count
            })

        # Pobierz projekty do filtra
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
        
        # Pobierz użytkowników do filtra (tylko dla adminów)
        users = []
        if current_user.is_admin:
            users = User.query.filter_by(is_active=True).order_by(User.display_name).all()

        return render_template('reports/worklog.html',
                             report_data=report_data,
                             projects=projects,
                             users=users,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'project_key': project_key,
                                 'user_id': user_id
                             })

    except Exception as e:
        logger.error(f"Error generating worklog report: {str(e)}", exc_info=True)
        flash('Wystąpił błąd podczas generowania raportu', 'error')
        return redirect(url_for('views.reports'))

@views_bp.route('/reports/project')
@login_required
def project_report():
    """Raport projektowy z bazy danych."""
    try:
        # Pobierz parametry filtrowania
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        project_key = request.args.get('project', None)

        # Domyślny zakres dat (ostatni miesiąc)
        if not start_date:
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')

        # Podstawowe zapytanie dla statystyk projektu
        query = db.session.query(
            Project.name.label('project_name'),
            Project.jira_key.label('project_key'),
            func.count(distinct(User.id)).label('user_count'),
            func.count(distinct(Issue.id)).label('issue_count'),
            func.sum(Worklog.time_spent_seconds).label('total_time')
        ).join(Worklog.project)\
         .join(Worklog.user)\
         .join(Worklog.issue)\
         .group_by(Project.id)

        # Dodaj filtry
        if start_date:
            query = query.filter(Worklog.work_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Worklog.work_date <= datetime.strptime(end_date, '%Y-%m-%d'))
        if project_key:
            query = query.filter(Project.jira_key == project_key)

        results = query.all()
        logger.info(f"Found {len(results)} projects with stats")

        # Przygotuj dane do raportu
        report_data = []
        for result in results:
            report_data.append({
                'project_name': result.project_name,
                'project_key': result.project_key,
                'user_count': result.user_count,
                'issue_count': result.issue_count,
                'total_hours': round(result.total_time / 3600, 2) if result.total_time else 0
            })

        # Pobierz projekty do filtra
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()

        return render_template('reports/project.html',
                             report_data=report_data,
                             projects=projects,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'project_key': project_key
                             })

    except Exception as e:
        logger.error(f"Error generating project report: {str(e)}", exc_info=True)
        flash('Wystąpił błąd podczas generowania raportu', 'error')
        return redirect(url_for('views.reports'))

@views_bp.route('/reports/user')
@login_required
def user_report():
    """Raport użytkownika z bazy danych."""
    try:
        # Pobierz parametry filtrowania
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        user_id = request.args.get('user_id', current_user.id)

        # Domyślny zakres dat (ostatni miesiąc)
        if not start_date:
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')

        # Podstawowe zapytanie
        query = db.session.query(
            User.display_name.label('user_name'),
            Project.name.label('project_name'),
            Issue.jira_key.label('issue_key'),
            Issue.summary.label('issue_summary'),
            db.func.sum(Worklog.time_spent_seconds).label('total_time'),
            db.func.count(Worklog.id).label('worklog_count')
        ).join(Worklog.user)\
         .join(Worklog.project)\
         .join(Worklog.issue)\
         .group_by(User.id, Project.id, Issue.id)

        # Dodaj filtry
        if start_date:
            query = query.filter(Worklog.work_date >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Worklog.work_date <= datetime.strptime(end_date, '%Y-%m-%d'))
        if user_id:
            query = query.filter(Worklog.user_id == user_id)
        elif not current_user.is_admin:
            # Jeśli nie jest adminem, pokaż tylko jego worklogi
            query = query.filter(Worklog.user_id == current_user.id)

        results = query.all()

        # Przygotuj dane do raportu
        report_data = []
        for result in results:
            report_data.append({
                'user_name': result.user_name,
                'project_name': result.project_name,
                'issue_key': result.issue_key,
                'issue_summary': result.issue_summary,
                'total_hours': round(result.total_time / 3600, 2),
                'worklog_count': result.worklog_count
            })

        # Pobierz użytkowników do filtra (tylko dla adminów)
        users = []
        if current_user.is_admin:
            users = User.query.filter_by(is_active=True).order_by(User.display_name).all()

        return render_template('reports/user.html',
                             report_data=report_data,
                             users=users,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'user_id': user_id
                             })

    except Exception as e:
        logger.error(f"Error generating user report: {str(e)}", exc_info=True)
        flash('Wystąpił błąd podczas generowania raportu', 'error')
        return redirect(url_for('views.reports'))

@views_bp.route('/reports/admin')
@login_required
@admin_required
def admin_report():
    """Raport administracyjny z bazy danych."""
    try:
        # Pobierz parametry filtrowania
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        report_type = request.args.get('report_type', 'users')

        # Domyślny zakres dat (ostatni miesiąc)
        if not start_date:
            end_date = datetime.now()
            start_date = (end_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')

        report_data = []
        if report_type == 'users':
            # Raport użytkowników
            query = db.session.query(
                User,
                func.count(distinct(ProjectAssignment.project_id)).label('project_count'),
                func.count(distinct(Worklog.id)).label('worklog_count'),
                func.max(Worklog.work_date).label('last_activity')
            ).select_from(User)\
             .outerjoin(ProjectAssignment)\
             .outerjoin(Worklog)\
             .group_by(User.id)

            results = query.all()
            logger.info(f"Found {len(results)} users")
            
            for result in results:
                user = result[0]
                report_data.append({
                    'display_name': user.display_name or user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'project_count': result.project_count,
                    'worklog_count': result.worklog_count,
                    'last_activity': result.last_activity
                })

        elif report_type == 'projects':
            # Raport projektów
            query = db.session.query(
                Project,
                func.count(distinct(ProjectAssignment.user_id)).label('user_count'),
                func.count(distinct(Issue.id)).label('issue_count'),
                func.sum(Worklog.time_spent_seconds / 3600).label('total_hours'),
                func.max(Worklog.work_date).label('last_activity')
            ).select_from(Project)\
             .outerjoin(ProjectAssignment)\
             .outerjoin(Issue, Issue.project_id == Project.id)\
             .outerjoin(Worklog, Worklog.project_id == Project.id)\
             .group_by(Project.id)

            results = query.all()
            logger.info(f"Found {len(results)} projects")
            
            for result in results:
                project = result[0]
                report_data.append({
                    'name': project.name,
                    'jira_key': project.jira_key,
                    'user_count': result.user_count,
                    'issue_count': result.issue_count,
                    'total_hours': result.total_hours or 0,
                    'last_activity': result.last_activity
                })

        else:  # activity
            # Raport aktywności
            query = db.session.query(
                func.date(Worklog.work_date).label('date'),
                func.count(distinct(User.id)).label('user_count'),
                func.count(Worklog.id).label('worklog_count'),
                func.sum(Worklog.time_spent_seconds / 3600).label('total_hours')
            ).select_from(Worklog)\
             .join(User)\
             .filter(Worklog.work_date.between(
                 datetime.strptime(start_date, '%Y-%m-%d'),
                 datetime.strptime(end_date, '%Y-%m-%d')
             ))\
             .group_by(func.date(Worklog.work_date))\
             .order_by(func.date(Worklog.work_date).desc())

            results = query.all()
            logger.info(f"Found activity data for {len(results)} days")
            
            for result in results:
                report_data.append({
                    'date': result.date,
                    'user_count': result.user_count,
                    'worklog_count': result.worklog_count,
                    'total_hours': result.total_hours or 0
                })

        return render_template('reports/admin.html',
                             report_data=report_data,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date,
                                 'report_type': report_type
                             })

    except Exception as e:
        logger.error(f"Error generating admin report: {str(e)}", exc_info=True)
        flash('Wystąpił błąd podczas generowania raportu', 'error')
        return redirect(url_for('views.reports'))

@views_bp.route('/teams/<int:team_id>/members/<user_name>/stats')
@auth_required(['admin', 'team_leader'])
def member_stats(team_id, user_name):
    """Wyświetla statystyki członka zespołu."""
    return render_template('teams/member_stats.html', team_id=team_id, user_name=user_name)

@views_bp.route('/teams/<int:team_id>/projects/<project_key>/stats')
@auth_required(['admin', 'team_leader'])
def project_stats(team_id, project_key):
    """Wyświetla statystyki projektu."""
    return render_template('teams/project_stats.html', team_id=team_id, project_key=project_key)

@views_bp.route('/admin')
@login_required
@admin_required
def admin():
    """Admin dashboard."""
    try:
        jira_service = get_jira_service()
        stats = {
            'users_count': get_users_count(),
            'active_users': get_active_users_count(),
            'total_worklogs': get_total_worklogs(),
            'total_projects': get_total_projects(),
            'jira_connected': jira_service.is_connected if jira_service else False,
            'last_sync': get_last_sync_time(),
            'system_status': get_system_status()
        }
        return render_template('admin/dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}", exc_info=True)
        stats = {
            'users_count': 0,
            'active_users': 0,
            'total_worklogs': 0,
            'total_projects': 0,
            'jira_connected': False,
            'last_sync': None,
            'system_status': 'error'
        }
        flash('Wystąpił błąd podczas ładowania danych.', 'danger')
        return render_template('admin/dashboard.html', stats=stats)

@views_bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """User management page."""
    try:
        users = User.query.all()
        roles = Role.query.all()
        form = UserForm()
        
        return render_template(
            'admin/users.html', 
            users=users, 
            roles=roles,
            form=form
        )
    except Exception as e:
        logger.error(f"Error loading users view: {str(e)}", exc_info=True)
        flash('Error loading users', 'error')
        return redirect(url_for('admin.index'))

@views_bp.route('/admin/users/save', methods=['POST'])
@login_required
@admin_required
def admin_users_save():
    """Zapisz zmiany użytkownika."""
    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        user_id = data.get('id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Brak ID użytkownika'
            }), 400

        user = User.query.get_or_404(user_id)
        logger.debug(f"Found user: {user.email}")
        
        # Aktualizuj role
        if 'roles' in data:
            roles = Role.query.filter(Role.id.in_(data['roles'])).all()
            logger.debug(f"Found roles: {[r.name for r in roles]}")
            user.roles = roles
            
        db.session.commit()
        logger.info(f"Updated roles for user {user.email}")
        
        return jsonify({
            'status': 'success',
            'message': 'Role użytkownika zostały zaktualizowane'
        })
        
    except Exception as e:
        logger.error(f"Error saving user roles: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/admin/users/delete/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_users_delete(user_id):
    """Usuń użytkownika."""
    try:
        user = User.query.get_or_404(user_id)
        
        if user.is_superadmin:
            return jsonify({
                'status': 'error',
                'message': 'Nie można usunąć superadmina'
            }), 400
            
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Użytkownik został usunięty'
        })
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    """Zarządzanie ustawieniami."""
    try:
        form = SettingsForm()
        
        if form.validate_on_submit():
            settings = {
                'SYNC_INTERVAL': str(form.sync_interval.data),
                'LOG_LEVEL': str(form.log_level.data),
                'CACHE_TIMEOUT': str(form.cache_timeout.data)
            }
            save_app_settings(settings)
            flash('Ustawienia zostały zaktualizowane.', 'success')
            return redirect(url_for('views.admin_settings'))
            
        # Pobierz aktualne ustawienia
        current_settings = {
            setting.name: setting.value 
            for setting in Setting.query.all()
        }
        
        # Wypełnij formularz aktualnymi wartościami
        if not form.is_submitted():
            form.sync_interval.data = int(current_settings.get('SYNC_INTERVAL', 3600))
            form.log_level.data = current_settings.get('LOG_LEVEL', '20')
            form.cache_timeout.data = int(current_settings.get('CACHE_TIMEOUT', 300))
        
        return render_template('admin/settings.html',
                             form=form,
                             current_settings=current_settings)
                             
    except Exception as e:
        logger.error(f"Error loading settings view: {str(e)}")
        flash('Wystąpił błąd podczas ładowania ustawień.', 'danger')
        return redirect(url_for('views.admin'))

@views_bp.route('/admin/logs')
@auth_required(['admin'])
def admin_logs():
    """Logi systemowe."""
    try:
        logs = get_system_logs()
        return render_template('admin/logs.html', logs=logs, form=FlaskForm())
    except Exception as e:
        logger.error(f"Error loading logs: {str(e)}")
        flash('Wystąpił błąd podczas ładowania logów.', 'danger')
        return render_template('admin/logs.html', logs=[], form=FlaskForm())

@views_bp.route('/favicon.ico')
def favicon():
    """Obsługa favicon.ico"""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@views_bp.errorhandler(404)
def not_found_error(error):
    """Obsługa błędu 404."""
    return render_template('404.html'), 404

@views_bp.route('/admin/backup')
@auth_required(['admin'])
def admin_backup():
    """Backup/restore systemu."""
    return render_template('admin/backup.html', form=FlaskForm())

@views_bp.route('/admin/backup/create', methods=['POST'])
@auth_required(['admin'])
def create_backup():
    """Utwórz backup systemu."""
    try:
        include_logs = request.form.get('include_logs', False)
        # TODO: Implementacja tworzenia backupu
        flash('Backup został utworzony.', 'success')
        return redirect(url_for('views.admin_backup'))
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        flash('Wystąpił błąd podczas tworzenia backupu.', 'danger')
        return redirect(url_for('views.admin_backup'))

@views_bp.route('/admin/backup/restore', methods=['POST'])
@auth_required(['admin'])
def restore_backup():
    """Przywróć backup systemu."""
    try:
        if 'backup_file' not in request.files:
            flash('Nie wybrano pliku.', 'danger')
            return redirect(url_for('views.admin_backup'))
            
        backup_file = request.files['backup_file']
        overwrite = request.form.get('overwrite', False)
        
        # TODO: Implementacja przywracania backupu
        flash('Backup został przywrócony.', 'success')
        return redirect(url_for('views.admin_backup'))
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        flash('Wystąpił błąd podczas przywracania backupu.', 'danger')
        return redirect(url_for('views.admin_backup'))

@views_bp.route('/admin/backup/<int:backup_id>/download')
@auth_required(['admin'])
def download_backup(backup_id):
    """Pobierz backup."""
    try:
        # TODO: Implementacja pobierania backupu
        return send_file(
            'path/to/backup.zip',
            as_attachment=True,
            download_name=f'backup_{backup_id}.zip'
        )
    except Exception as e:
        logger.error(f"Error downloading backup: {str(e)}")
        flash('Wystąpił błąd podczas pobierania backupu.', 'danger')
        return redirect(url_for('views.admin_backup'))

@views_bp.route('/admin/backup/<int:backup_id>/delete', methods=['POST'])
@auth_required(['admin'])
def delete_backup(backup_id):
    """Usuń backup."""
    try:
        # TODO: Implementacja usuwania backupu
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views_bp.route('/admin/jira')
@login_required
@admin_required
def admin_jira():
    """Konfiguracja połączenia z Jira."""
    try:
        form = JiraConfigForm()
        jira_config = JiraConfig.query.filter_by(is_active=True).first()
        
        if jira_config:
            form.jira_url.data = jira_config.url
            form.jira_username.data = jira_config.username
            
        return render_template('admin/jira.html', 
                             form=form,
                             jira_status=is_jira_connected(),
                             config=current_app.config)
    except Exception as e:
        logger.error(f"Jira config error: {str(e)}")
        flash('Wystąpił błąd podczas ładowania konfiguracji Jira.', 'danger')
        return redirect(url_for('views.admin'))

@views_bp.route('/api/jira/test-connection', methods=['POST'])
@login_required
@admin_required
def test_jira_connection():
    """Test JIRA connection."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Brak danych konfiguracyjnych'
            }), 400

        url = data.get('url')
        username = data.get('username')
        api_token = data.get('api_token')

        if not all([url, username, api_token]):
            return jsonify({
                'status': 'error',
                'message': 'Wszystkie pola są wymagane'
            }), 400

        success, message = test_connection(url, username, api_token)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message
        })

    except Exception as e:
        logger.error(f"Error testing JIRA connection: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Wystąpił błąd: {str(e)}'
        }), 500

@views_bp.route('/admin/jira/save', methods=['POST'])
@login_required
@admin_required
def save_jira_config_endpoint():
    """Zapisz konfigurację JIRA."""
    try:
        form = JiraConfigForm()
        
        if form.validate_on_submit():
            data = {
                'url': form.jira_url.data,
                'username': form.jira_username.data,
                'api_token': form.jira_token.data if form.jira_token.data else None
            }
            
            success, message = save_jira_config(data)
            if success:
                flash('Konfiguracja JIRA została zapisana.', 'success')
            else:
                flash(f'Wystąpił błąd: {message}', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
            
        return redirect(url_for('views.admin_jira'))
        
    except Exception as e:
        logger.error(f"Error saving JIRA config: {str(e)}")
        flash('Wystąpił błąd podczas zapisywania konfiguracji.', 'danger')
        return redirect(url_for('views.admin_jira'))

@views_bp.route('/static/<path:filename>')
def static_files(filename):
    """Obsługa plików statycznych."""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        filename
    )

@views_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('errors/500.html'), 500

@views_bp.errorhandler(Exception)
def handle_error(error):
    """Globalna obsługa błędów dla views_bp."""
    logger.error(f"View error: {str(error)}")
    return jsonify({'status': 'error', 'message': 'Wystąpił nieoczekiwany błąd'}), 500

@views_bp.route('/view/<int:user_id>')
@login_required
def view_user(user_id):
    try:
        # Get the requested user's data
        user = User.query.get_or_404(user_id)  # Use .query.get_or_404 instead of direct call
        
        return render_template('user/view.html', user=user)
    except Exception as e:
        logger.error(f"View error: {str(e)}")
        return render_template('errors/500.html'), 500

@views_bp.route('/activity')
@login_required
@log_errors
def activity():
    """User activity history."""
    user = User.query.get(current_user.id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    worklogs = user.worklogs.order_by(Worklog.created_at.desc()).all()
    
    return render_template('activity.html',
                         user=user,
                         worklogs=worklogs)

@views_bp.route('/project/<int:project_id>')
@login_required
@log_errors
@check_project_access
def project_details(project_id):
    """Project details view."""
    try:
        project = Project.query.get_or_404(project_id)
        team_members = project.team.members if project.team else []
        project_logs = project.worklogs.order_by(Worklog.created_at.desc()).limit(10).all()
        
        return render_template('project_details.html',
                             project=project,
                             team_members=team_members,
                             recent_activity=project_logs)
    except Exception as e:
        logger.error(f"Error in project_details: {str(e)}")
        flash('Error loading project details', 'error')
        return redirect(url_for('views.dashboard'))

@views_bp.route('/team/<int:team_id>')
@login_required
@log_errors
@check_team_access
def team_details(team_id):
    """Team details view."""
    try:
        team = Team.query.get_or_404(team_id)
        team_projects = team.team_projects.all()
        return render_template('team_details.html',
                             team=team,
                             projects=team_projects)
    except Exception as e:
        logger.error(f"Error in team_details: {str(e)}")
        flash('Error loading team details', 'error')
        return redirect(url_for('views.dashboard'))

@views_bp.route('/settings')
@login_required
def settings():
    """Ustawienia użytkownika."""
    try:
        form = UserSettingsForm()
        if current_user:
            form.display_name.data = current_user.display_name
            form.email.data = current_user.email
        return render_template('views/settings.html', form=form)
    except Exception as e:
        logger.error(f"Settings view error: {str(e)}")
        flash('Wystąpił błąd podczas ładowania ustawień.', 'danger')
        return redirect(url_for('views.dashboard'))

@views_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Aktualizacja ustawień użytkownika."""
    try:
        form = UserSettingsForm()
        if form.validate_on_submit():
            current_user.display_name = form.display_name.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Ustawienia zostały zaktualizowane.', 'success')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    except Exception as e:
        logger.error(f"Settings update error: {str(e)}")
        flash('Wystąpił błąd podczas aktualizacji ustawień.', 'danger')
    
    return redirect(url_for('views.settings'))

@views_bp.route('/profile')
@login_required
def profile():
    """Profil użytkownika."""
    try:
        return render_template('views/profile.html', user=current_user)
    except Exception as e:
        logger.error(f"Profile view error: {str(e)}")
        flash('Wystąpił błąd podczas ładowania profilu.', 'danger')
        return redirect(url_for('views.dashboard'))

@views_bp.route('/teams/<int:team_id>/members')
@login_required
@admin_required
def team_members(team_id):
    """Członkowie zespołu."""
    try:
        team = Team.query.get_or_404(team_id)
        members = team.members
        return render_template('teams/team_members.html', team=team, members=members)
    except Exception as e:
        logger.error(f"Error loading team members: {str(e)}")
        flash('Error loading team members', 'error')
        return redirect(url_for('views.dashboard'))

@views_bp.route('/teams/<int:team_id>/projects')
@login_required
@admin_required
def team_projects(team_id):
    """Projekty zespołu."""
    try:
        team = Team.query.get_or_404(team_id)
        projects = team.projects
        return render_template('teams/team_projects.html', team=team, projects=projects)
    except Exception as e:
        logger.error(f"Error loading team projects: {str(e)}")
        flash('Error loading team projects', 'error')
        return redirect(url_for('views.dashboard'))

@views_bp.route('/api/admin/users/import', methods=['POST'])
@login_required
@admin_required
def import_jira_users():
    """Import users from JIRA."""
    try:
        jira_service = JiraService()
        if not jira_service.client:
            raise ValueError("Could not connect to JIRA")

        # Upewnij się, że rola 'user' istnieje
        default_role = Role.query.filter_by(name='user').first()
        if not default_role:
            current_app.logger.info("Creating default user role")
            default_role = Role(
                name='user',
                description='Default user role'
            )
            db.session.add(default_role)
            db.session.commit()
            current_app.logger.info("Default role created successfully")

        current_app.logger.info("Starting JIRA users import...")
        
        # Pobierz użytkowników z JIRA
        start_at = 0
        max_results = 50
        all_users = []
        processed_emails = set()  # Zbiór do śledzenia unikalnych emaili
        
        while True:
            try:
                current_app.logger.debug(f"Fetching users batch: startAt={start_at}, maxResults={max_results}")
                result = jira_service.get_users(start_at=start_at, max_results=max_results)
                users = result.get('values', [])
                current_app.logger.debug(f"Retrieved batch of {len(users)} users")
                
                if not users:
                    break

                # Dodaj tylko unikalnych użytkowników
                for user in users:
                    email = user.get('emailAddress')
                    if email and email not in processed_emails:
                        all_users.append(user)
                        processed_emails.add(email)
                
                current_app.logger.info(f"Total unique users retrieved: {len(all_users)}")
                
                if result.get('isLast', True):
                    break
                    
                start_at += max_results
            except Exception as e:
                current_app.logger.error(f"Error fetching users batch: {str(e)}")
                break

        if not all_users:
            current_app.logger.warning("No users found in JIRA")
            return jsonify({
                'status': 'warning',
                'message': 'Nie znaleziono użytkowników w JIRA'
            }), 404

        # Importuj użytkowników
        stats = {
            'added': 0,
            'updated': 0,
            'errors': 0,
            'total_users': len(all_users),
            'unique_users': len(processed_emails)
        }

        current_app.logger.info(f"Starting import of {len(all_users)} unique users")

        # Pobierz wszystkich istniejących użytkowników do słownika dla szybszego wyszukiwania
        existing_users = {
            user.email: user for user in User.query.all()
        }

        for jira_user in all_users:
            try:
                email = jira_user['emailAddress']
                if not email:
                    current_app.logger.warning(f"Skipping user {jira_user['name']} - no email address")
                    stats['errors'] += 1
                    continue

                user = existing_users.get(email)
                
                if user:
                    # Aktualizuj istniejącego użytkownika
                    user.email = email
                    user.display_name = jira_user['displayName']
                    user.is_active = jira_user['active']
                    user.username = jira_user['name']
                    
                    # Sprawdź i dodaj rolę
                    if not user.roles:
                        user.roles = [default_role]
                        current_app.logger.info(f"Added default role to existing user: {user.username}")
                    elif default_role not in user.roles:
                        user.roles.append(default_role)
                        current_app.logger.info(f"Added default role to existing user: {user.username}")
                    
                    stats['updated'] += 1
                    current_app.logger.debug(f"Updated user: {user.username} ({email})")
                else:
                    # Dodaj nowego użytkownika
                    user = User(
                        username=jira_user['name'],
                        email=email,
                        display_name=jira_user['displayName'],
                        is_active=jira_user['active'],
                        roles=[default_role]  # Dodaj rolę bezpośrednio przy tworzeniu
                    )
                    db.session.add(user)
                    existing_users[email] = user
                    stats['added'] += 1
                    current_app.logger.info(f"Added new user: {user.username} ({email}) with default role")

            except Exception as e:
                current_app.logger.error(f"Error importing user {jira_user.get('name', 'unknown')}: {str(e)}")
                stats['errors'] += 1
                continue

        # Upewnij się, że wszyscy użytkownicy mają rolę
        users_without_roles = User.query.filter(~User.roles.any()).all()
        if users_without_roles:
            current_app.logger.info(f"Found {len(users_without_roles)} users without roles, adding default role")
            for user in users_without_roles:
                user.roles = [default_role]
                current_app.logger.info(f"Added default role to user: {user.username}")

        db.session.commit()
        current_app.logger.info(f"Import completed. Stats: {stats}")
        
        return jsonify({
            'status': 'success',
            'message': f"Zaimportowano {stats['added']} nowych i zaktualizowano {stats['updated']} użytkowników",
            'stats': stats
        })

    except Exception as e:
        current_app.logger.error(f"Error importing JIRA users: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/users')
@login_required
def get_users_api():
    try:
        users = User.query.all()
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'displayName': user.display_name,
            'isActive': user.is_active,
            'roles': [role.name for role in user.roles],
            'projects': len(user.projects) if user.projects else 0,
            'lastActivity': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
        } for user in users])
    except Exception as e:
        current_app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@views_bp.route('/api/admin/projects/sync', methods=['POST'])
@login_required
@admin_required
def sync_jira_projects():
    """Synchronizuj projekty z JIRA."""
    try:
        jira_service = JiraService()
        if not jira_service.client:
            raise ValueError("Brak połączenia z JIRA")

        current_app.logger.info("Rozpoczęto synchronizację projektów z JIRA...")
        
        stats = jira_service.sync_projects()
        
        return jsonify({
            'status': 'success',
            'message': f"Zsynchronizowano {stats['added']} nowych i zaktualizowano {stats['updated']} projektów",
            'stats': stats
        })

    except Exception as e:
        current_app.logger.error(f"Błąd podczas synchronizacji projektów: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/projects')
@login_required
def get_projects():
    """Pobierz listę projektów."""
    try:
        projects = Project.query.all()
        return jsonify([project.to_dict() for project in projects])
    except Exception as e:
        current_app.logger.error(f"Error getting projects: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/admin/projects', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_projects():
    """Zarządzanie projektami."""
    try:
        form = ProjectForm()
        
        if form.validate_on_submit():
            project = Project(
                name=form.name.data,
                jira_key=form.jira_key.data,
                description=form.description.data,
                is_active=form.is_active.data
            )
            db.session.add(project)
            db.session.commit()
            flash('Projekt został dodany.', 'success')
            return redirect(url_for('views.admin_projects'))
            
        projects = Project.query.all()
        csrf_token = generate_csrf()
        
        return render_template('admin/projects.html',
                             projects=projects,
                             form=form,
                             csrf_token=csrf_token)
    except Exception as e:
        current_app.logger.error(f"Error loading projects view: {str(e)}", exc_info=True)
        flash('Wystąpił błąd podczas ładowania projektów.', 'danger')
        return redirect(url_for('views.admin'))

@views_bp.route('/admin/jira-config', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_jira_config():
    """Konfiguracja JIRA."""
    try:
        form = JiraConfigForm()
        
        if form.validate_on_submit():
            jira_config = JiraConfig.query.filter_by(is_active=True).first()
            if not jira_config:
                jira_config = JiraConfig()
                db.session.add(jira_config)
            
            jira_config.url = form.jira_url.data
            jira_config.username = form.jira_username.data
            if form.jira_token.data:  # Update token only if provided
                jira_config.api_token = form.jira_token.data
            jira_config.is_active = True
            
            db.session.commit()
            
            # Test connection with new credentials
            success = test_connection(
                url=jira_config.url,
                username=jira_config.username,
                api_token=jira_config.api_token
            )
            
            if success:
                flash('Konfiguracja JIRA została zapisana i połączenie działa.', 'success')
            else:
                flash('Konfiguracja zapisana, ale test połączenia nie powiódł się.', 'warning')
                
            return redirect(url_for('views.admin_jira_config'))
            
        # Fill form with current config
        jira_config = JiraConfig.query.filter_by(is_active=True).first()
        if jira_config and not form.is_submitted():
            form.jira_url.data = jira_config.url
            form.jira_username.data = jira_config.username
            
        return render_template('admin/jira_config.html',
                             form=form,
                             current_config=jira_config)
                             
    except Exception as e:
        logger.error(f"Error loading JIRA config view: {str(e)}")
        flash('Wystąpił błąd podczas ładowania konfiguracji JIRA.', 'danger')
        return redirect(url_for('views.admin'))

@views_bp.route('/api/projects/<project_key>')
@login_required
def get_project_details(project_key):
    """Pobiera szczegóły projektu."""
    try:
        jira_service = JiraService()
        if not jira_service.is_connected:
            return jsonify({
                'status': 'error',
                'message': 'Nie można połączyć się z JIRA'
            }), 500

        # Pobierz projekt z JIRA
        project = jira_service.get_project(project_key)
        if not project:
            return jsonify({
                'status': 'error',
                'message': f'Projekt {project_key} nie został znaleziony'
            }), 404

        # Pobierz dodatkowe statystyki
        issues_count = jira_service.count_project_issues(project_key)
        active_users = jira_service.get_project_users(project_key)
        last_update = jira_service.get_project_last_update(project_key)

        return jsonify({
            'status': 'success',
            'key': project.key,
            'name': project.name,
            'description': getattr(project, 'description', ''),
            'issues_count': issues_count,
            'active_users': len(active_users),
            'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None
        })

    except Exception as e:
        logger.error(f"Error getting project details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/worklogs')
@login_required
def get_worklogs():
    """Pobiera worklogi dla wybranego okresu."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.utcnow() - timedelta(days=7)
            
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_date = datetime.utcnow()

        jira_service = JiraService()
        if not jira_service.is_connected:
            raise Exception("Nie można połączyć się z JIRA")

        # Pobierz worklogi w zależności od roli użytkownika
        if current_user.has_role('admin'):
            worklogs = jira_service.get_all_worklogs(start_date, end_date)
        else:
            worklogs = jira_service.get_user_worklogs(current_user.username, start_date, end_date)

        # Grupuj worklogi
        grouped_worklogs = {}
        for worklog in worklogs:
            project_key = worklog['issue'].split('-')[0]
            username = worklog.get('author', current_user.username)
            
            if project_key not in grouped_worklogs:
                grouped_worklogs[project_key] = {}
            
            if username not in grouped_worklogs[project_key]:
                grouped_worklogs[project_key][username] = []
                
            grouped_worklogs[project_key][username].append(worklog)

        # Renderuj tylko część HTML z worklogami
        html = render_template('worklog_results.html',
                             grouped_worklogs=grouped_worklogs,
                             jira_url=jira_service.server)  # Dodaj URL JIRA
                             
        return jsonify({
            'status': 'success',
            'html': html
        })

    except Exception as e:
        logger.error(f"Error getting worklogs: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/projects/list', methods=['GET'])
@login_required
def get_projects_list():
    """Pobiera listę projektów z bazy danych."""
    try:
        logger.info("Starting get_projects_list endpoint")
        
        # Pobierz projekty z bazy danych
        projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
        logger.info(f"Found {len(projects)} projects in database")
        
        if not projects:
            logger.warning("No projects found in database")
            response = jsonify({
                'status': 'success',
                'projects': []
            })
            return response

        project_list = []
        for project in projects:
            try:
                project_list.append({
                    'key': project.jira_key,
                    'name': project.name,
                    'display_name': f"{project.jira_key} - {project.name}"
                })
            except Exception as e:
                logger.error(f"Error processing project {project.id}: {str(e)}")
                continue

        logger.info(f"Returning {len(project_list)} projects")
        
        return jsonify({
            'status': 'success',
            'projects': project_list
        })

    except Exception as e:
        logger.error(f"Error getting projects list: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Dodaj obsługę OPTIONS dla CORS
@views_bp.route('/api/projects/list', methods=['OPTIONS'])
def projects_list_options():
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
    return response

@views_bp.route('/api/reports/worklog', methods=['POST'])
@login_required
def generate_worklog_report():
    """Generuje raport worklogów."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Brak danych'
            }), 400

        start_date = datetime.strptime(data['date_start'], '%Y-%m-%d')
        end_date = datetime.strptime(data['date_end'], '%Y-%m-%d')
        project_key = data.get('project_key')

        jira_service = JiraService()
        if not jira_service.is_connected:
            raise Exception("Nie można połączyć się z JIRA")

        # Pobierz worklogi
        if current_user.has_role('admin'):
            worklogs = jira_service.get_all_worklogs(start_date, end_date)
        else:
            worklogs = jira_service.get_user_worklogs(current_user.username, start_date, end_date)

        # Filtruj po projekcie jeśli podano
        if project_key:
            worklogs = [w for w in worklogs if w.get('project') == project_key]

        # Grupuj worklogi według projektu i użytkownika
        grouped_worklogs = {}
        for worklog in worklogs:
            project_key = worklog.get('project', 'Brak projektu')
            username = worklog.get('author', current_user.username)
            
            if project_key not in grouped_worklogs:
                grouped_worklogs[project_key] = {}
            
            if username not in grouped_worklogs[project_key]:
                grouped_worklogs[project_key][username] = []
                
            grouped_worklogs[project_key][username].append(worklog)

        # Renderuj szablon z wynikami
        html = render_template('reports/worklog_results.html',
                             grouped_worklogs=grouped_worklogs,
                             start_date=start_date,
                             end_date=end_date,
                             jira_url=jira_service.server)

        return jsonify({
            'status': 'success',
            'html': html
        })

    except Exception as e:
        logger.error(f"Error generating worklog report: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/reports/worklog/export')
@login_required
def export_worklog_report():
    """Eksportuje raport worklogów do Excela."""
    try:
        start_date = datetime.strptime(request.args.get('date_start'), '%Y-%m-%d')
        end_date = datetime.strptime(request.args.get('date_end'), '%Y-%m-%d')
        project_key = request.args.get('project_key')

        jira_service = JiraService()
        if not jira_service.is_connected:
            raise Exception("Nie można połączyć się z JIRA")

        # Pobierz worklogi
        if current_user.has_role('admin'):
            worklogs = jira_service.get_all_worklogs(start_date, end_date)
        else:
            worklogs = jira_service.get_user_worklogs(current_user.username, start_date, end_date)

        # Filtruj po projekcie jeśli podano
        if project_key:
            worklogs = [w for w in worklogs if w.get('project') == project_key]

        # Utwórz Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Nagłówki
        headers = ['Projekt', 'Użytkownik', 'Zadanie', 'Czas (h)', 'Data', 'Komentarz']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Dane
        row = 1
        for worklog in worklogs:
            worksheet.write(row, 0, worklog.get('project', ''))
            worksheet.write(row, 1, worklog.get('author', ''))
            worksheet.write(row, 2, worklog.get('issue', ''))
            worksheet.write(row, 3, worklog.get('time_spent', 0))
            worksheet.write(row, 4, worklog.get('work_date', ''))
            worksheet.write(row, 5, worklog.get('comment', ''))
            row += 1

        workbook.close()
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'worklog_report_{start_date.strftime("%Y-%m-%d")}_{end_date.strftime("%Y-%m-%d")}.xlsx'
        )

    except Exception as e:
        logger.error(f"Error exporting worklog report: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/users/<int:user_id>/roles', methods=['GET', 'POST', 'DELETE'])
@login_required
@admin_required
def manage_user_roles(user_id):
    """Zarządzanie rolami użytkownika."""
    try:
        user = User.query.get_or_404(user_id)
        
        if request.method == 'GET':
            # Pobierz role użytkownika
            user_roles = [role.to_dict() for role in user.roles]
            available_roles = [role.to_dict() for role in Role.query.all() 
                             if role not in user.roles]
            
            return jsonify({
                'status': 'success',
                'user_roles': user_roles,
                'available_roles': available_roles
            })
            
        elif request.method == 'POST':
            # Dodaj rolę do użytkownika
            data = request.get_json()
            role_id = data.get('role_id')
            
            if not role_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Nie podano ID roli'
                }), 400
                
            role = Role.query.get_or_404(role_id)
            
            if role in user.roles:
                return jsonify({
                    'status': 'error',
                    'message': 'Użytkownik ma już tę rolę'
                }), 400
                
            user.roles.append(role)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Dodano rolę {role.name} do użytkownika {user.username}'
            })
            
        elif request.method == 'DELETE':
            # Usuń rolę użytkownika
            data = request.get_json()
            role_id = data.get('role_id')
            
            if not role_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Nie podano ID roli'
                }), 400
                
            role = Role.query.get_or_404(role_id)
            
            if role not in user.roles:
                return jsonify({
                    'status': 'error',
                    'message': 'Użytkownik nie ma tej roli'
                }), 400
                
            user.roles.remove(role)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Usunięto rolę {role.name} z użytkownika {user.username}'
            })
            
    except Exception as e:
        logger.error(f"Error managing user roles: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@views_bp.route('/api/roles', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_roles():
    """Zarządzanie rolami."""
    try:
        if request.method == 'GET':
            # Pobierz wszystkie role
            roles = [role.to_dict() for role in Role.query.all()]
            return jsonify({
                'status': 'success',
                'roles': roles
            })
            
        elif request.method == 'POST':
            # Utwórz nową rolę
            data = request.get_json()
            name = data.get('name')
            description = data.get('description')
            permissions = data.get('permissions', [])
            
            if not name:
                return jsonify({
                    'status': 'error',
                    'message': 'Nazwa roli jest wymagana'
                }), 400
                
            if Role.query.filter_by(name=name).first():
                return jsonify({
                    'status': 'error',
                    'message': 'Rola o tej nazwie już istnieje'
                }), 400
                
            role = Role(
                name=name,
                description=description,
                permissions=json.dumps(permissions)
            )  # Dodano brakujący nawias zamykający
            db.session.add(role)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Utworzono rolę {name}',
                'role': role.to_dict()
            })
            
        elif request.method == 'PUT':
            # Aktualizuj rolę
            data = request.get_json()
            role_id = data.get('id')
            
            if not role_id:
                return jsonify({
                    'status': 'error',
                    'message': 'ID roli jest wymagane'
                }), 400
                
            role = Role.query.get_or_404(role_id)
            
            if 'name' in data:
                role.name = data['name']
            if 'description' in data:
                role.description = data['description']
            if 'permissions' in data:
                role.permissions = json.dumps(data['permissions'])
                
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Zaktualizowano rolę {role.name}',
                'role': role.to_dict()
            })
            
        elif request.method == 'DELETE':
            # Usuń rolę
            data = request.get_json()
            role_id = data.get('id')
            
            if not role_id:
                return jsonify({
                    'status': 'error',
                    'message': 'ID roli jest wymagane'
                }), 400
                
            role = Role.query.get_or_404(role_id)
            
            if role.name in ['admin', 'user']:
                return jsonify({
                    'status': 'error',
                    'message': 'Nie można usunąć roli systemowej'
                }), 400
                
            db.session.delete(role)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Usunięto rolę {role.name}'
            })
            
    except Exception as e:
        logger.error(f"Error managing roles: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 