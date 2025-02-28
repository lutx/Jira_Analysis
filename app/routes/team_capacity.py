from flask import Blueprint, jsonify, request, render_template
from app.models import TeamCapacity, TeamAllocation, Team, Project, User
from app.extensions import db
from app.utils.auth import requires_auth, requires_admin
from datetime import datetime
import logging
from typing import Dict

logger = logging.getLogger(__name__)
team_capacity_bp = Blueprint('team_capacity', __name__)

@team_capacity_bp.route('/team-capacity')
@requires_auth
def index():
    """Team capacity management view."""
    try:
        teams = Team.query.all()
        projects = Project.query.filter_by(is_active=True).all()
        current_date = datetime.utcnow()
        
        return render_template(
            'team_capacity/index.html',
            teams=teams,
            projects=projects,
            current_date=current_date
        )
    except Exception as e:
        logger.error(f"Error loading team capacity view: {str(e)}")
        return render_template('error.html', error=str(e))

@team_capacity_bp.route('/api/team-capacity', methods=['GET'])
@requires_auth
def get_team_capacities():
    """Get team capacities for all teams."""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        team_id = request.args.get('team_id', type=int)
        
        if not year or not month:
            now = datetime.utcnow()
            year = year or now.year
            month = month or now.month
        
        query = TeamCapacity.query
        if team_id:
            query = query.filter_by(team_id=team_id)
        
        capacities = query.filter_by(year=year, month=month).all()
        
        # Get team members count for each capacity
        capacity_data = []
        for capacity in capacities:
            data = capacity.to_dict()
            data['team_members'] = User.query.filter_by(team_id=capacity.team_id, is_active=True).count()
            capacity_data.append(data)
        
        return jsonify({
            'status': 'success',
            'data': capacity_data
        }), 200
    except Exception as e:
        logger.error(f"Error getting team capacities: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@team_capacity_bp.route('/api/team-capacity/<int:team_id>', methods=['GET'])
@requires_auth
def get_team_capacity(team_id: int):
    """Get team capacity for specific team."""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        if not year or not month:
            now = datetime.utcnow()
            year = year or now.year
            month = month or now.month
        
        capacity = TeamCapacity.get_or_create(team_id, year, month)
        
        return jsonify({
            'status': 'success',
            'data': capacity.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error getting team capacity: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@team_capacity_bp.route('/api/team-capacity/<int:team_id>/allocations', methods=['GET'])
@requires_auth
def get_team_allocations(team_id: int):
    """Get project allocations for team capacity."""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        if not year or not month:
            now = datetime.utcnow()
            year = year or now.year
            month = month or now.month
        
        capacity = TeamCapacity.get_or_create(team_id, year, month)
        allocations = capacity.allocations.order_by(TeamAllocation.priority.desc()).all()
        
        return jsonify({
            'status': 'success',
            'data': [a.to_dict() for a in allocations]
        }), 200
    except Exception as e:
        logger.error(f"Error getting team allocations: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@team_capacity_bp.route('/api/team-capacity/<int:team_id>/allocations', methods=['POST'])
@requires_admin
def create_team_allocation(team_id: int):
    """Create new project allocation for team capacity."""
    try:
        data = request.get_json()
        year = data.get('year', datetime.utcnow().year)
        month = data.get('month', datetime.utcnow().month)
        
        # Validate required fields
        required_fields = ['project_id', 'allocated_hours']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        capacity = TeamCapacity.get_or_create(team_id, year, month)
        
        # Check if allocation already exists
        existing = TeamAllocation.query.filter_by(
            capacity_id=capacity.id,
            project_id=data['project_id']
        ).first()
        
        if existing:
            return jsonify({
                'status': 'error',
                'message': 'Allocation already exists for this project'
            }), 400
        
        # Check if enough capacity available
        if capacity.available_capacity < data['allocated_hours']:
            return jsonify({
                'status': 'error',
                'message': 'Not enough capacity available'
            }), 400
        
        allocation = TeamAllocation(
            capacity_id=capacity.id,
            project_id=data['project_id'],
            allocated_hours=data['allocated_hours'],
            priority=data.get('priority', 1),
            notes=data.get('notes')
        )
        
        db.session.add(allocation)
        capacity.allocated_capacity += data['allocated_hours']
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Allocation created successfully',
            'data': allocation.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating team allocation: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@team_capacity_bp.route('/api/team-capacity/allocations/<int:allocation_id>', methods=['PUT'])
@requires_admin
def update_team_allocation(allocation_id: int):
    """Update existing project allocation."""
    try:
        allocation = TeamAllocation.query.get_or_404(allocation_id)
        data = request.get_json()
        
        # Update allocation hours if provided
        if 'allocated_hours' in data:
            old_hours = allocation.allocated_hours
            new_hours = float(data['allocated_hours'])
            
            # Check if enough capacity available
            capacity_change = new_hours - old_hours
            if capacity_change > 0 and allocation.capacity.available_capacity < capacity_change:
                return jsonify({
                    'status': 'error',
                    'message': 'Not enough capacity available'
                }), 400
            
            allocation.allocated_hours = new_hours
            allocation.capacity.allocated_capacity += capacity_change
        
        # Update other fields
        if 'priority' in data:
            allocation.priority = data['priority']
        if 'notes' in data:
            allocation.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Allocation updated successfully',
            'data': allocation.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating team allocation: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@team_capacity_bp.route('/api/team-capacity/allocations/<int:allocation_id>', methods=['DELETE'])
@requires_admin
def delete_team_allocation(allocation_id: int):
    """Delete project allocation."""
    try:
        allocation = TeamAllocation.query.get_or_404(allocation_id)
        capacity = allocation.capacity
        
        # Update team capacity
        capacity.allocated_capacity -= allocation.allocated_hours
        
        db.session.delete(allocation)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Allocation deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting team allocation: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@team_capacity_bp.route('/api/team-capacity/<int:team_id>/recalculate', methods=['POST'])
@requires_admin
def recalculate_team_capacity(team_id: int):
    """Recalculate team capacity for given period."""
    try:
        data = request.get_json()
        year = data.get('year', datetime.utcnow().year)
        month = data.get('month', datetime.utcnow().month)
        
        capacity = TeamCapacity.get_or_create(team_id, year, month)
        total_capacity = capacity.calculate_total_capacity()
        
        return jsonify({
            'status': 'success',
            'message': 'Capacity recalculated successfully',
            'data': {
                'total_capacity': total_capacity,
                'capacity': capacity.to_dict()
            }
        }), 200
    except Exception as e:
        logger.error(f"Error recalculating team capacity: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 