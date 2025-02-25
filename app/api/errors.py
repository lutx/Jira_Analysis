from flask import jsonify
from app.api import api_bp
from app.exceptions import BaseAppException, ValidationError

@api_bp.errorhandler(BaseAppException)
def handle_app_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@api_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({
        'error': 'validation_error',
        'message': str(error),
        'errors': error.errors
    }), 400

@api_bp.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'error': 'not_found',
        'message': 'Resource not found'
    }), 404

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'internal_server_error',
        'message': 'An unexpected error occurred'
    }), 500 