from flask import Blueprint, render_template, send_from_directory, redirect, url_for
from flask_login import login_required, current_user
from app.models import Project
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html')

@main_bp.route('/projects')
@login_required
def projects():
    """Projects list view."""
    projects = Project.query.all()
    return render_template('main/projects.html', projects=projects)

@main_bp.route('/projects/<int:project_id>')
@login_required
def project_details(project_id):
    """Project details view."""
    project = Project.query.get_or_404(project_id)
    return render_template('main/project_details.html', project=project)

@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(main_bp.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    ) 