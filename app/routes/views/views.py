from flask import render_template, g, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
from app.routes.views import views_bp
from app.models import Project
import logging

logger = logging.getLogger(__name__)

@views_bp.route('/projects')
@login_required
def projects():
    """Display all projects."""
    projects = Project.query.all()
    return render_template('views/projects.html', projects=projects)

# ... rest of your views ... 