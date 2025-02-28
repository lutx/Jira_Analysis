from flask import Blueprint, jsonify, request
from app.models.role import Role
from app.extensions import db
from app.utils.auth import requires_auth, requires_admin
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)
roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/api/roles', methods=['GET'])
@requires_auth
def get_roles():
    """Get all roles with optional analytics."""
    try:
        include_analytics = request.args.get('include_analytics', 'false').lower() == 'true'
        roles = Role.query.all()
        return jsonify({
            'status': 'success',
            'data': [r.to_dict() if include_analytics else {
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'job_function': r.job_function,
                'job_function_display': Role.JOB_FUNCTIONS.get(r.job_function, r.job_function),
                'permissions': r.get_permissions()
            } for r in roles]
        }), 200
    except Exception as e:
        logger.error(f"Error getting roles: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@roles_bp.route('/api/roles/<int:role_id>', methods=['GET'])
@requires_auth
def get_role(role_id: int):
    """Get detailed information about a specific role."""
    try:
        role = Role.query.get_or_404(role_id)
        include_analytics = request.args.get('include_analytics', 'false').lower() == 'true'
        return jsonify({
            'status': 'success',
            'data': role.to_dict() if include_analytics else {
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'job_function': role.job_function,
                'job_function_display': Role.JOB_FUNCTIONS.get(role.job_function, role.job_function),
                'permissions': role.get_permissions()
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting role: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@roles_bp.route('/api/roles/<int:role_id>/analytics', methods=['GET'])
@requires_auth
def get_role_analytics(role_id: int):
    """Get detailed analytics for a specific role."""
    try:
        role = Role.query.get_or_404(role_id)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Convert date strings to datetime objects if provided
        start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        
        analytics = {
            'workload_statistics': role.get_workload_statistics(start_date, end_date),
            'project_distribution': role.get_project_distribution()
        }
        
        return jsonify({
            'status': 'success',
            'data': analytics
        }), 200
    except Exception as e:
        logger.error(f"Error getting role analytics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@roles_bp.route('/api/roles', methods=['POST'])
@requires_admin
def create_role():
    """Create a new role."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate job function if provided
        if 'job_function' in data and data['job_function'] not in Role.JOB_FUNCTIONS:
            return jsonify({
                'status': 'error',
                'message': f'Invalid job function. Must be one of: {", ".join(Role.JOB_FUNCTIONS.keys())}'
            }), 400
            
        # Create new role
        role = Role(
            name=data['name'],
            description=data['description'],
            job_function=data.get('job_function'),
            hourly_rate=data.get('hourly_rate', 0.0),
            permissions=data.get('permissions', [])
        )
        
        db.session.add(role)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Role created successfully',
            'data': role.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating role: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@roles_bp.route('/api/roles/<int:role_id>', methods=['PUT'])
@requires_admin
def update_role(role_id: int):
    """Update an existing role."""
    try:
        role = Role.query.get_or_404(role_id)
        data = request.get_json()
        
        # Update basic fields
        if 'name' in data:
            role.name = data['name']
        if 'description' in data:
            role.description = data['description']
            
        # Update job function if valid
        if 'job_function' in data:
            if data['job_function'] not in Role.JOB_FUNCTIONS:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid job function. Must be one of: {", ".join(Role.JOB_FUNCTIONS.keys())}'
                }), 400
            role.job_function = data['job_function']
            
        # Update hourly rate
        if 'hourly_rate' in data:
            role.hourly_rate = float(data['hourly_rate'])
            
        # Update permissions
        if 'permissions' in data:
            role.set_permissions(data['permissions'])
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Role updated successfully',
            'data': role.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating role: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@roles_bp.route('/api/roles/job-functions', methods=['GET'])
@requires_auth
def get_job_functions():
    """Get list of available job functions."""
    try:
        return jsonify({
            'status': 'success',
            'data': Role.JOB_FUNCTIONS
        }), 200
    except Exception as e:
        logger.error(f"Error getting job functions: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@roles_bp.route('/api/roles/permissions', methods=['GET'])
@requires_auth
def get_permissions():
    """Get list of available permissions."""
    try:
        return jsonify({
            'status': 'success',
            'data': Role.PERMISSIONS
        }), 200
    except Exception as e:
        logger.error(f"Error getting permissions: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 