from flask import Flask, render_template, session
from flask_wtf.csrf import CSRFProtect
from config import config

csrf = CSRFProtect()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Konfiguracja
    app.config.from_object(config[config_name])
    
    # Inicjalizacja rozszerzeń
    csrf.init_app(app)
    
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
    # Rejestracja blueprintów
    from .routes import auth_bp, views_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(views_bp)
    
    # Rejestracja globalnych obsług błędów
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
        
    @app.errorhandler(401)
    def unauthorized_error(error):
        return render_template('errors/401.html'), 401
        
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    return app 