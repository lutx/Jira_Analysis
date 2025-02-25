from flask import Blueprint, jsonify, request
from app.models import Role, Team, Project, Portfolio, User
from app.extensions import db
from app.api.auth import api_admin_required

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/admin/roles')
@api_admin_required
def get_roles():
    """Get roles for DataTables."""
    # Get parameters from DataTables
    draw = request.args.get('draw', type=int)
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)
    search = request.args.get('search[value]')
    
    # Base query
    query = Role.query
    
    # Apply search
    if search:
        query = query.filter(Role.name.ilike(f'%{search}%'))
    
    # Get total and filtered count
    total_count = Role.query.count()
    filtered_count = query.count()
    
    # Apply pagination
    roles = query.offset(start).limit(length).all()
    
    # Format data for DataTables
    data = [{
        'id': role.id,
        'name': role.name,
        'description': role.description,
        'permissions': role.permissions
    } for role in roles]
    
    return jsonify({
        'draw': draw,
        'recordsTotal': total_count,
        'recordsFiltered': filtered_count,
        'data': data
    }) 