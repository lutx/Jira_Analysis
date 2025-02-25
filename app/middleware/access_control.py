from functools import wraps
from flask import abort, current_app, flash, redirect, url_for
from flask_login import current_user

def check_project_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if not project_id or not current_user.can_access_project(project_id):
            flash('You do not have access to this project.', 'error')
            return redirect(url_for('views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def check_team_access(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        team_id = kwargs.get('team_id')
        if not team_id or not (current_user.is_superadmin or 
                              any(team.id == team_id for team in current_user.teams)):
            flash('You do not have access to this team.', 'error')
            return redirect(url_for('views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function 