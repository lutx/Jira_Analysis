from flask import jsonify, render_template, request, flash, redirect, url_for
from werkzeug.exceptions import HTTPException
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import logging
from flask_sqlalchemy import SQLAlchemy
from app import app
from flask_wtf.csrf import CSRFError

logger = logging.getLogger(__name__)
db = SQLAlchemy()

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': 'internal_server_error',
                'message': 'An unexpected error occurred'
            }), 500
            
        return render_template('errors/500.html'), 500

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle all HTTP exceptions."""
        logger.warning(f"HTTP error {error.code}: {str(error)}")
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'error': error.name.lower(),
                'message': str(error)
            }), error.code
            
        return render_template(f'errors/{error.code}.html'), error.code

    @app.errorhandler(JWTExtendedException)
    def handle_jwt_error(error):
        """Handle JWT authentication errors."""
        logger.warning(f"JWT error: {str(error)}")
        
        return jsonify({
            'error': 'unauthorized',
            'message': str(error)
        }), 401

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': 'Not found'
            }), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': 'Internal server error',
                'details': str(error)
            }), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Handle CSRF errors."""
        logger.error(f"CSRF error: {str(e)}")
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'CSRF token missing or invalid'
            }), 400
        flash('Błąd bezpieczeństwa. Proszę spróbować ponownie.', 'danger')
        return redirect(url_for('auth.login')) 