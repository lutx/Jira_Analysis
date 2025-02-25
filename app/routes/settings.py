from flask import Blueprint, render_template, g, flash, redirect, url_for, request, jsonify
from app.utils.decorators import auth_required, admin_required
from flask_wtf import FlaskForm
from flask_login import login_required
from flask_login import current_user
from app.models.user import User
from app.forms.profile import ProfileForm
from app.extensions import db
from app.forms.settings import GeneralSettingsForm

# Zmiana nazwy blueprintu z system_settings_bp na settings_bp
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    """Display settings index page."""
    form = GeneralSettingsForm(obj=None)
    if current_user.settings:
        form.language.data = current_user.settings.get('language', 'en')
        form.timezone.data = current_user.settings.get('timezone', 'UTC')
        form.date_format.data = current_user.settings.get('date_format', 'YYYY-MM-DD')
    return render_template('settings/general.html', form=form)

@settings_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        if form.current_password.data and not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('settings/profile.html', form=form)
            
        current_user.display_name = form.display_name.data
        current_user.email = form.email.data
        
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
            
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('settings.profile'))
        
    return render_template('settings/profile.html', form=form)

@settings_bp.route('/admin')
@login_required
def admin():
    """Admin settings."""
    return render_template('settings/admin.html')

@settings_bp.route('/save', methods=['POST'])
@login_required
def save_settings():
    """Save general settings."""
    form = GeneralSettingsForm()
    if form.validate_on_submit():
        # Save settings to database or config file
        current_user.settings = {
            'language': form.language.data,
            'timezone': form.timezone.data,
            'date_format': form.date_format.data
        }
        db.session.commit()
        flash('Settings saved successfully.', 'success')
    return redirect(url_for('settings.index'))

@settings_bp.route('/admin/save', methods=['POST'])
@admin_required
def save_admin_settings():
    """Save admin settings."""
    form = FlaskForm()
    if form.validate_on_submit():
        # Implementacja zapisu ustawień administracyjnych
        flash('Ustawienia administracyjne zostały zapisane.', 'success')
        return redirect(url_for('settings.admin'))
    return redirect(url_for('settings.admin')) 