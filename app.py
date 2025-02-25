from flask import Flask, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException
import os
from app.models.database import db, init_db
from app.models.user import User
from app.models.team import Team
from app.models.team_membership import TeamMembership as TeamMember
from app.models.role import Role
from app.models.user_role import UserRole
from app.exceptions import AppException
from app import create_app
from app.utils.logger import setup_logger
from blueprints.error_handlers import error_handlers
from flask_login import LoginManager, login_required, logout_user
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from config import Config
from app.extensions import migrate, scheduler, csrf

# Initialize Flask extensions
db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'login'
    
    # Register error handlers
    @app.errorhandler(AppException)
    def handle_app_exception(error):
        response = error.to_dict()
        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        if isinstance(error, HTTPException):
            return jsonify(error=str(error)), error.code
        app.logger.error(f"Unhandled exception: {str(error)}")
        return jsonify(error="Internal Server Error"), 500
    
    # Register blueprints
    from app.main import bp as main_bp
    from app.auth import bp as auth_bp
    from app.admin import bp as admin_bp
    from app.portfolios import bp as portfolios_bp
    from app.worklog import bp as worklog_bp
    from app.reports import bp as reports_bp
    from app.user import bp as user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(portfolios_bp, url_prefix='/portfolios')
    app.register_blueprint(worklog_bp, url_prefix='/worklog')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(error_handlers)
    
    @app.route('/')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/admin')
    @login_required
    def admin():
        return render_template('admin.html')

    @app.route('/reports')
    @login_required
    def reports():
        return render_template('reports.html')

    @app.route('/analytics')
    @login_required
    def analytics():
        return render_template('analytics.html')

    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))
    
    # Jira synchronization scheduler
    @scheduler.task('cron', id='sync_jira', hour='*/1')
    def sync_jira_data():
        with app.app_context():
            from app.tasks.jira_sync import sync_all
            sync_all()

    scheduler.start()

    return app

def init_test_data(app):
    """Inicjalizuje podstawowe dane testowe."""
    with app.app_context():
        try:
            # 1. Tworzenie roli superadmina
            superadmin_role = Role.query.filter_by(name='superadmin').first()
            if not superadmin_role:
                superadmin_role = Role(
                    name='superadmin',
                    description='Super Administrator systemu',
                    permissions=['all']
                )
                db.session.add(superadmin_role)
                db.session.flush()
            
            # 2. Tworzenie użytkownika superadmina
            superadmin = User.query.filter_by(username='admin').first()
            if not superadmin:
                superadmin = User(
                    username='admin',
                    email='admin@example.com',
                    display_name='Administrator',
                    is_active=True,
                    is_superadmin=True
                )
                superadmin.set_password('admin')
                db.session.add(superadmin)
                db.session.flush()  # Aby uzyskać ID superadmina
                
                # 3. Przypisanie roli superadmina
                user_role = UserRole(
                    user_id=superadmin.id,
                    role_id=superadmin_role.id,
                    assigned_by=superadmin.id  # Superadmin przypisuje sobie rolę
                )
                db.session.add(user_role)
                
                # 4. Utworzenie zespołu administratorów
                admin_team = Team(
                    name='Administrators',
                    description='Team for administrators',
                    leader=superadmin
                )
                db.session.add(admin_team)
                
                # 5. Dodanie superadmina do zespołu
                admin_team.add_user(superadmin, role='leader')
                
                db.session.commit()
                print("\n✓ Superadmin account created successfully")
                print(f"Email: {superadmin.email}")
                print("Password: admin")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error creating superadmin: {str(e)}")
            db.session.rollback()
            return False

app = create_app()
setup_logger(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003) 