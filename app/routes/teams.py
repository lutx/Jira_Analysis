from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.team import Team
from app.models.user import User
from app.extensions import db
from app.utils.decorators import admin_required
import logging

teams_bp = Blueprint('teams', __name__, url_prefix='/teams')
logger = logging.getLogger(__name__)

@teams_bp.route('/<int:team_id>/members', methods=['POST'])
@login_required
@admin_required
def add_team_member(team_id):
    """Add member to team."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'User ID is required'
            }), 400
            
        team = Team.query.get_or_404(team_id)
        user = User.query.get_or_404(user_id)
        
        if user in team.members:
            return jsonify({
                'status': 'error',
                'message': 'User is already a member of this team'
            }), 400
            
        team.members.append(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Member added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding team member: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@teams_bp.route('/<int:team_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def remove_team_member(team_id, user_id):
    """Remove member from team."""
    try:
        team = Team.query.get_or_404(team_id)
        user = User.query.get_or_404(user_id)
        
        if user not in team.members:
            return jsonify({
                'status': 'error',
                'message': 'User is not a member of this team'
            }), 400
            
        team.members.remove(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Member removed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error removing team member: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 