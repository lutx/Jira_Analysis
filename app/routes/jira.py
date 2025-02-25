from flask import Blueprint, jsonify, request
import requests
from config import JIRA_BASE_URL, JIRA_API_TOKEN, JIRA_USERNAME

jira_bp = Blueprint('jira', __name__)

@jira_bp.route('/api/jira/fetch-users', methods=['GET'])
def fetch_jira_users():
    try:
        start_at = request.args.get('startAt', default=0, type=int)
        max_results = request.args.get('maxResults', default=50, type=int)
        
        url = f"{JIRA_BASE_URL}/rest/api/2/group/member"
        params = {
            'includeInactiveUsers': 'false',
            'maxResults': max_results,
            'groupname': 'jira-software-users',
            'startAt': start_at
        }
        
        response = requests.get(
            url,
            params=params,
            auth=(JIRA_USERNAME, JIRA_API_TOKEN),
            verify=False  # Only if needed for self-signed certificates
        )
        
        response.raise_for_status()
        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

@jira_bp.route('/api/jira/import-users', methods=['POST'])
def import_jira_users():
    try:
        users = request.json.get('users', [])
        
        # Here implement your logic to save users to your database
        # Example:
        # for user in users:
        #     save_user_to_database(user)
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {len(users)} users'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 