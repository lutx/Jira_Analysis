from flask import Blueprint, render_template, request, flash, redirect, url_for, g, jsonify, current_app
from app.utils.decorators import auth_required, admin_required
from app.services.portfolio_service import (
    get_all_portfolios, get_portfolio, create_portfolio, update_portfolio,
    add_project_to_portfolio, remove_project_from_portfolio,
    get_portfolio_stats, assign_user_to_project
)
from flask_wtf import FlaskForm
from flask_wtf.csrf import generate_csrf
from flask_login import login_required, current_user
from app.models import Portfolio, Project
from app.extensions import db
from app.forms.portfolio import PortfolioForm
import logging
from app.utils.auth import requires_auth
from datetime import datetime
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')
logger = logging.getLogger(__name__)

@portfolio_bp.route('/')
@login_required
def index():
    projects = Project.query.all()
    return render_template('portfolio/index.html', projects=projects)

@portfolio_bp.route('/list')
@login_required
def list():
    """Lista portfolii."""
    portfolios = Portfolio.query.all()
    return render_template('portfolio/list.html', portfolios=portfolios)

@portfolio_bp.route('/overview')
@login_required
def overview():
    """Przegląd portfolio."""
    try:
        portfolios = Portfolio.query.filter_by(owner_id=current_user.id).all()
        return render_template('portfolio/overview.html', portfolios=portfolios)
    except Exception as e:
        logger.error(f"Error loading portfolio overview: {str(e)}")
        return render_template('portfolio/overview.html', error=str(e))

@portfolio_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    """Tworzenie nowego portfolio."""
    form = PortfolioForm()
    
    if request.method == 'POST':
        # Log request data for debugging
        logger.debug(f"Form data: {request.form}")
        logger.debug(f"CSRF token in form: {request.form.get('csrf_token')}")
        
        if form.validate_on_submit():
            try:
                portfolio = Portfolio(
                    name=form.name.data,
                    description=form.description.data,
                    is_active=True,
                    created_by=current_user.username
                )
                
                db.session.add(portfolio)
                db.session.commit()
                flash('Portfolio zostało utworzone.', 'success')
                return redirect(url_for('portfolio.list'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating portfolio: {str(e)}")
                flash('Wystąpił błąd podczas tworzenia portfolio.', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')
                    logger.error(f"Form validation error - {field}: {error}")
    
    # Generate new CSRF token for GET requests
    if request.method == 'GET':
        form.csrf_token.data = generate_csrf()
    
    if form.validate_on_submit():
        portfolio = Portfolio(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(portfolio)
        db.session.commit()
        flash('Portfolio zostało utworzone.', 'success')
        return redirect(url_for('portfolio.list'))
    return render_template('portfolio/create.html', form=form)

@portfolio_bp.route('/<int:portfolio_id>')
@login_required
def view(portfolio_id):
    """Szczegóły portfolio."""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    return render_template('portfolio/view.html', portfolio=portfolio)

@portfolio_bp.route('/<int:portfolio_id>/update', methods=['POST'])
@auth_required(['admin'])
def update(portfolio_id):
    """Aktualizuj portfolio."""
    try:
        if not request.form.get('name'):
            return jsonify({'status': 'error', 'message': 'Nazwa jest wymagana'}), 400
            
        portfolio_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'client_name': request.form.get('client_name')
        }
        
        if update_portfolio(portfolio_id, portfolio_data):
            flash('Portfolio zostało zaktualizowane.', 'success')
        else:
            flash('Wystąpił błąd podczas aktualizacji portfolio.', 'danger')
            
        return redirect(url_for('portfolio.view', portfolio_id=portfolio_id))
    except Exception as e:
        logger.error(f"Error updating portfolio {portfolio_id}: {str(e)}")
        flash('Wystąpił błąd podczas aktualizacji portfolio.', 'danger')
        return redirect(url_for('portfolio.view', portfolio_id=portfolio_id))

@portfolio_bp.route('/<int:portfolio_id>/projects/add', methods=['POST'])
@auth_required(['admin'])
def add_project(portfolio_id):
    """Dodaj projekt do portfolio."""
    try:
        project_key = request.form.get('project_key')
        if not project_key:
            return jsonify({'status': 'error', 'message': 'Klucz projektu jest wymagany'}), 400
            
        if add_project_to_portfolio(portfolio_id, project_key, g.user['username']):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Nie można dodać projektu'})
    except Exception as e:
        logger.error(f"Error adding project to portfolio {portfolio_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@portfolio_bp.route('/<int:portfolio_id>/projects/<project_key>/remove', methods=['POST'])
@auth_required(['admin'])
def remove_project(portfolio_id, project_key):
    """Usuń projekt z portfolio."""
    try:
        if remove_project_from_portfolio(portfolio_id, project_key):
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Nie można usunąć projektu'})
    except Exception as e:
        logger.error(f"Error removing project from portfolio {portfolio_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@portfolio_bp.route('/portfolios', methods=['POST'])
def create_portfolio_json():
    """Create new portfolio."""
    data = request.get_json()
    portfolio = create_portfolio(data)
    return jsonify(portfolio.to_dict()), 201

@portfolio_bp.route('/portfolios/<int:portfolio_id>/assignments', methods=['POST'])
def assign_user():
    """Assign user to project in portfolio."""
    data = request.get_json()
    assignment = assign_user_to_project(**data)
    return jsonify(assignment.to_dict()), 201

@portfolio_bp.route('/portfolios/<int:portfolio_id>/stats')
def get_stats():
    """Get portfolio statistics."""
    month = request.args.get('month')
    stats = get_portfolio_stats(portfolio_id, month)
    return jsonify(stats)

@portfolio_bp.route('/api/portfolios', methods=['GET'])
@requires_auth
def get_portfolios():
    """Get all portfolios with optional analytics."""
    try:
        include_analytics = request.args.get('include_analytics', 'false').lower() == 'true'
        portfolios = Portfolio.query.all()
        return jsonify({
            'status': 'success',
            'data': [p.to_dict() if include_analytics else {
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'projects_count': len(p.projects)
            } for p in portfolios]
        }), 200
    except Exception as e:
        logger.error(f"Error getting portfolios: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@portfolio_bp.route('/api/portfolios/<int:portfolio_id>/analytics', methods=['GET'])
@requires_auth
def get_portfolio_analytics(portfolio_id: int):
    """Get detailed analytics for a specific portfolio."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Convert date strings to datetime objects if provided
        start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        
        analytics = {
            'role_distribution': portfolio.get_role_distribution(start_date, end_date),
            'hours_analysis': portfolio.get_planned_vs_actual_hours(start_date, end_date),
            'project_statistics': portfolio.get_project_statistics()
        }
        
        return jsonify({
            'status': 'success',
            'data': analytics
        }), 200
    except Exception as e:
        logger.error(f"Error getting portfolio analytics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@portfolio_bp.route('/api/portfolios/<int:portfolio_id>/projects', methods=['GET'])
@requires_auth
def get_portfolio_projects(portfolio_id: int):
    """Get all projects in a portfolio with their analytics."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        include_analytics = request.args.get('include_analytics', 'false').lower() == 'true'
        
        projects_data = []
        for project in portfolio.projects:
            project_data = project.to_dict()
            if include_analytics:
                project_data.update({
                    'role_distribution': project.get_role_distribution(),
                    'hours_analysis': project.get_planned_vs_actual_hours()
                })
            projects_data.append(project_data)
            
        return jsonify({
            'status': 'success',
            'data': projects_data
        }), 200
    except Exception as e:
        logger.error(f"Error getting portfolio projects: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@portfolio_bp.route('/api/portfolios/<int:portfolio_id>/shadow-work', methods=['GET'])
@requires_auth
def get_portfolio_shadow_work(portfolio_id: int):
    """Get analysis of work logged outside assigned projects in the portfolio."""
    try:
        portfolio = Portfolio.query.get_or_404(portfolio_id)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Convert date strings to datetime objects if provided
        start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        
        from app.models.worklog import Worklog
        from app.models.project_assignment import ProjectAssignment
        
        # Get all worklogs for unassigned projects
        shadow_work_query = db.session.query(
            Worklog.user_id,
            Worklog.project_id,
            db.func.sum(Worklog.hours_spent).label('hours')
        ).outerjoin(
            ProjectAssignment,
            db.and_(
                ProjectAssignment.user_id == Worklog.user_id,
                ProjectAssignment.project_id == Worklog.project_id
            )
        ).filter(
            ProjectAssignment.id.is_(None),
            Worklog.project_id.in_([p.id for p in portfolio.projects])
        )
        
        if start_date:
            shadow_work_query = shadow_work_query.filter(Worklog.date >= start_date)
        if end_date:
            shadow_work_query = shadow_work_query.filter(Worklog.date <= end_date)
            
        shadow_work = shadow_work_query.group_by(
            Worklog.user_id,
            Worklog.project_id
        ).all()
        
        # Get user and project details
        from app.models.user import User
        from app.models.project import Project
        
        shadow_work_analysis = []
        for user_id, project_id, hours in shadow_work:
            user = User.query.get(user_id)
            project = Project.query.get(project_id)
            if user and project:
                shadow_work_analysis.append({
                    'user': user.to_dict(),
                    'project': project.to_dict(),
                    'hours': float(hours)
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'shadow_work': shadow_work_analysis,
                'total_hours': sum(sw['hours'] for sw in shadow_work_analysis)
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting portfolio shadow work: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@portfolio_bp.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Portfolio error: {str(error)}")
    return jsonify({'status': 'error', 'message': 'Wystąpił nieoczekiwany błąd'}), 500 