from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, logout_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
@login_required
def index():
    """Main index page."""
    return render_template('main/index.html', page_title="Home")

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page."""
    return render_template('main/dashboard.html', page_title="Dashboard")

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    return render_template('main/profile.html', page_title="My Profile")

@main_bp.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    return redirect(url_for('main.index')) 