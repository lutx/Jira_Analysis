from flask import render_template, current_app, redirect, url_for, jsonify, request
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Bad request"}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized"}), 401
        return render_template('errors/401.html'), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Forbidden"}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "Not found"}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({"error": "Internal server error"}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(401)
    def unauthorized_error(error):
        current_app.logger.warning(f"401 error: {request.url}")
        return redirect(url_for('views.login'))

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json:
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Method Not Allowed',
                'message': f'Method {request.method} not allowed for this endpoint'
            }), 405
        return render_template('errors/405.html'), 405 