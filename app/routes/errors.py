@bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    if request.path.startswith('/static/'):
        return jsonify({
            'error': 'Static file not found',
            'path': request.path
        }), 404
    return render_template('errors/404.html'), 404 