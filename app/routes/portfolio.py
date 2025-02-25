from flask import Blueprint, render_template, request, flash, redirect, url_for, g, jsonify
from app.utils.decorators import auth_required, admin_required
from app.services.portfolio_service import (
    get_all_portfolios, get_portfolio, create_portfolio, update_portfolio,
    add_project_to_portfolio, remove_project_from_portfolio,
    get_portfolio_stats, assign_user_to_project
)
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from app.models import Portfolio, Project
from app.extensions import db
from app.forms.portfolio import PortfolioForm
import logging

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

@portfolio_bp.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Portfolio error: {str(error)}")
    return jsonify({'status': 'error', 'message': 'Wystąpił nieoczekiwany błąd'}), 500 