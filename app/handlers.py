from flask import jsonify
from flask_wtf.csrf import CSRFError

def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return jsonify({
            'error': 'CSRF token validation failed',
            'message': str(e)
        }), 400 