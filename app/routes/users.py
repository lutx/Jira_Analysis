from flask import Blueprint, request, jsonify
from flask_login import login_required
from sqlalchemy import or_
from app.models.user import User
from app.services.jira_service import sync_jira_users
from app.utils.logger import logger

# Create blueprint
users_bp = Blueprint('users', __name__)

@users_bp.route('/api/users/search')
@login_required
def search_users():
    """Search users API endpoint."""
    query = request.args.get('q', '')
    
    try:
        users = User.query
        
        if query:
            users = users.filter(
                or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%'),
                    User.display_name.ilike(f'%{query}%')
                )
            )
        
        users = users.all()
        return jsonify({
            'status': 'success',
            'users': [user.to_dict() for user in users]
        })
        
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@users_bp.route('/api/users/import-from-jira', methods=['POST'])
@login_required
def import_users_from_jira():
    """Import users from JIRA."""
    try:
        stats = sync_jira_users()
        return jsonify({
            'status': 'success',
            'message': 'Users imported successfully',
            **stats
        })
    except Exception as e:
        logger.error(f"Error importing users from JIRA: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 