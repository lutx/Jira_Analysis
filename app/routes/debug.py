from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models import User, Role

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')

@debug_bp.route('/health')
def health_check():
    """Basic health check endpoint"""
    return jsonify({"status": "healthy", "message": "Server is running"}), 200

@debug_bp.route('/debug/users')
@jwt_required()
def list_users():
    """Debug endpoint to list all users"""
    try:
        users = User.query.all()
        return jsonify({
            "status": "success",
            "users": [
                {
                    "id": user.id,
                    "email": user.email,
                    "is_active": user.is_active,
                    "roles": [role.name for role in user.roles]
                } for user in users
            ]
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@debug_bp.route('/debug/roles')
@jwt_required()
def list_roles():
    """Debug endpoint to list all roles"""
    try:
        roles = Role.query.all()
        return jsonify({
            "status": "success",
            "roles": [
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "users": [user.email for user in role.users]
                } for role in roles
            ]
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500 