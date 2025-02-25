from flask import Blueprint, jsonify, request
from app.decorators import auth_required
from app.models import User, Role, Team
from app.schemas import UserSchema, RoleSchema, TeamSchema
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/users', methods=['GET'])
@auth_required(['admin'])
def get_users():
    """Get all users."""
    try:
        users = User.query.all()
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'display_name': user.display_name,
            'is_active': user.is_active
        } for user in users])
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/roles', methods=['GET'])
@auth_required(['admin'])
def get_roles():
    """Get all roles."""
    roles = Role.query.all()
    return jsonify(RoleSchema(many=True).dump(roles)) 