from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Project, Portfolio, User
from app.extensions import db
from app.forms.project import ProjectForm
import logging

projects_bp = Blueprint('projects', __name__)
logger = logging.getLogger(__name__)

@projects_bp.route('/')
@login_required
def index():
    """Lista projektów."""
    try:
        projects = Project.query.all()
        return render_template('main/projects.html', projects=projects)
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}")
        flash("An error occurred while fetching projects.", "error")
        return render_template('main/projects.html', projects=[])

@projects_bp.route('/create')
@login_required
def create():
    return render_template('main/projects/create.html')

@projects_bp.route('/<int:project_id>')
@login_required
def view(project_id):
    """Szczegóły projektu."""
    try:
        project = Project.query.get_or_404(project_id)
        return render_template('main/project_details.html', project=project)
    except Exception as e:
        logger.error(f"Error fetching project {project_id}: {str(e)}")
        flash("An error occurred while fetching the project.", "error")
        return redirect(url_for('projects.index'))

@projects_bp.route('/my')
@login_required
def my_projects():
    """Moje projekty."""
    try:
        projects = current_user.projects
        return render_template('main/projects.html', projects=projects)
    except Exception as e:
        logger.error(f"Error fetching user projects: {str(e)}")
        flash("An error occurred while fetching your projects.", "error")
        return render_template('main/projects.html', projects=[]) 