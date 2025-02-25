from flask import Blueprint, jsonify, request, current_app, make_response, g, session
from app.utils.decorators import auth_required, admin_required
from app.services.jira_service import get_jira_service, get_jira_projects, JiraService
from app.services.worklog_service import WorklogService
from datetime import datetime, timedelta
import logging
from flask_login import login_required, current_user
from app.models.role import Role
from app.models.user import User
from app.models.team import Team
from app.extensions import db
from functools import wraps
import uuid
from app.services.report_service import get_workload_report
from flask_wtf.csrf import CSRFProtect
from app.models.worklog import Worklog
from app.models.project import Project

logger = logging.getLogger(__name__)

# Utwórz blueprint tylko raz
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Add CSRF exemption for specific API routes if needed
csrf = CSRFProtect()

def json_response(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                data, status_code = response
            else:
                data, status_code = response, 200
                
            if not isinstance(data, dict):
                data = {'data': data}
                
            return jsonify(data), status_code
            
        except Exception as e:
            current_app.logger.error(f"Error in JSON response: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
            
    return decorated_function

@api_bp.route('/health')
def health_check():
    return jsonify({"status": "ok"})

@api_bp.route('/protected')
@auth_required()
def protected():
    return jsonify({"message": "This is a protected endpoint"})

@api_bp.route('/jira/status', methods=['GET'])
@auth_required()
def jira_status():
    try:
        jira = get_jira_service()
        jira.connect()  # Test połączenia
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Jira connection error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/issues', methods=['GET'])
@auth_required()
def get_issues():
    """Pobiera listę zadań z Jiry."""
    try:
        jql = request.args.get('jql', '')
        jira = get_jira_service()
        issues = jira.search_issues(jql)
        return jsonify(issues)
    except Exception as e:
        logger.error(f"Error getting issues: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania zadań"}), 500

@api_bp.route('/issue/<issue_key>', methods=['GET'])
@auth_required()
def get_issue(issue_key):
    """Pobiera szczegóły zadania z Jiry."""
    try:
        jira = get_jira_service()
        issue = jira.get_issue(issue_key)
        if not issue:
            return jsonify({"error": "Zadanie nie istnieje"}), 404
        return jsonify(issue)
    except Exception as e:
        logger.error(f"Error getting issue {issue_key}: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania zadania"}), 500

@api_bp.route('/issue/<issue_key>/worklog', methods=['GET'])
@auth_required()
def get_worklog(issue_key):
    """Pobiera worklog dla zadania."""
    try:
        jira = get_jira_service()
        worklogs = jira.get_worklogs(issue_key)
        return jsonify(worklogs)
    except Exception as e:
        logger.error(f"Error getting worklog for {issue_key}: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania worklogu"}), 500

@api_bp.route('/issue/<issue_key>/worklog', methods=['POST'])
@auth_required()
def add_worklog(issue_key):
    """Dodaje worklog do zadania."""
    try:
        data = request.get_json()
        if not data or 'timeSpent' not in data:
            return jsonify({"error": "Brak wymaganego pola timeSpent"}), 400
            
        jira = get_jira_service()
        success = jira.add_worklog(
            issue_key,
            data['timeSpent'],
            data.get('comment', '')
        )
        
        if success:
            return jsonify({"message": "Worklog został dodany"})
        else:
            return jsonify({"error": "Nie udało się dodać worklogu"}), 500
            
    except Exception as e:
        logger.error(f"Error adding worklog to {issue_key}: {str(e)}")
        return jsonify({"error": "Błąd podczas dodawania worklogu"}), 500

@api_bp.route('/projects', methods=['GET'])
@auth_required()
def get_projects():
    """Pobiera listę projektów z Jiry."""
    try:
        jira = get_jira_service()
        projects = jira.get_projects()
        return jsonify(projects)
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        return jsonify({"error": "Błąd podczas pobierania projektów"}), 500

@api_bp.route('/users/jira')
@auth_required()
def get_jira_users():
    """Get users from JIRA."""
    try:
        jira = get_jira_service()
        users = jira.get_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Error getting JIRA users: {str(e)}")
        return jsonify({"error": "Failed to get JIRA users"}), 500

@api_bp.route('/users/app')
@login_required
def get_app_users():
    """Get all application users."""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@api_bp.route('/worklogs', methods=['GET'])
@auth_required()
def get_worklogs():
    """Get worklogs with statistics."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        project_key = request.args.get('project_key')
        
        # Convert dates
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
        # Base query with eager loading
        base_query = Worklog.query\
            .options(
                db.joinedload(Worklog.user),
                db.joinedload(Worklog.project),
                db.joinedload(Worklog.issue)
            )

        # Stats query
        stats_query = db.session.query(
            db.func.count(Worklog.id).label('total_count'),
            db.func.sum(Worklog.time_spent_seconds).label('total_time'),
            db.func.count(db.distinct(Worklog.user_id)).label('active_users')
        )

        # Apply filters to both queries
        if start_date:
            base_query = base_query.filter(Worklog.work_date >= start_date)
            stats_query = stats_query.filter(Worklog.work_date >= start_date)
        if end_date:
            base_query = base_query.filter(Worklog.work_date <= end_date)
            stats_query = stats_query.filter(Worklog.work_date <= end_date)
        if project_key:
            base_query = base_query.join(Project).filter(Project.jira_key == project_key)
            stats_query = stats_query.join(Project).filter(Project.jira_key == project_key)

        # If not admin, show only user's worklogs
        if not current_user.is_admin:
            base_query = base_query.filter(Worklog.user_id == current_user.id)
            stats_query = stats_query.filter(Worklog.user_id == current_user.id)

        # Get statistics
        stats = stats_query.first()
        total_count = stats.total_count or 0
        total_hours = round((stats.total_time or 0) / 3600, 2)
        active_users = stats.active_users or 0

        # Calculate average daily hours
        avg_daily_hours = 0
        if start_date and end_date and total_hours > 0:
            days = (end_date - start_date).days + 1
            if days > 0:
                avg_daily_hours = round(total_hours / days, 2)

        # Get worklogs with sorting
        base_query = base_query.order_by(Worklog.work_date.desc())
        worklogs = base_query.all()

        # Prepare worklog data
        worklog_data = []
        for worklog in worklogs:
            worklog_data.append({
                'id': worklog.id,
                'user': {
                    'id': worklog.user.id,
                    'name': worklog.user.display_name or worklog.user.username
                },
                'project': {
                    'id': worklog.project.id,
                    'name': worklog.project.name,
                    'key': worklog.project.jira_key
                },
                'issue': {
                    'id': worklog.issue.id,
                    'key': worklog.issue.jira_key,
                    'summary': worklog.issue.summary
                },
                'time_spent_seconds': worklog.time_spent_seconds,
                'time_spent_hours': round(worklog.time_spent_seconds / 3600, 2),
                'work_date': worklog.work_date.strftime('%Y-%m-%d'),
                'description': worklog.description,
                'created_at': worklog.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify({
            'status': 'success',
            'worklogs': worklog_data,
            'stats': {
                'total_count': total_count,
                'total_hours': total_hours,
                'active_users': active_users,
                'avg_daily_hours': avg_daily_hours
            }
        })

    except Exception as e:
        logger.error(f"Error getting worklogs: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/worklogs', methods=['POST'])
@auth_required()
def create_worklog():
    """Create a new worklog entry."""
    try:
        data = request.get_json()
        data['user_name'] = g.current_user['user_name']
        
        worklog = WorklogService.create_worklog(data)
        return jsonify(worklog.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating worklog: {str(e)}")
        return jsonify({"error": "Błąd podczas tworzenia worklogu"}), 500

@api_bp.route('/worklogs/sync', methods=['POST'])
@auth_required(['admin'])
def sync_worklogs():
    """Manually trigger worklog synchronization."""
    try:
        days = request.json.get('days', 30)
        stats = WorklogService.sync_jira_worklogs(days)
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error syncing worklogs: {str(e)}")
        return jsonify({"error": "Błąd podczas synchronizacji worklogów"}), 500

@api_bp.route('/activity-data')
@auth_required()
def get_activity_data():
    """Pobiera dane aktywności dla wybranego okresu."""
    period = request.args.get('period', '7d')
    
    # Mapowanie okresów na dni
    period_days = {
        '7d': 7,
        '30d': 30,
        '90d': 90
    }
    
    days = period_days.get(period, 7)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    try:
        jira = get_jira_service()
        user = session['user']['user_name']
        
        # Przygotuj daty dla wykresu
        dates = [(end_date - timedelta(days=x)).strftime('%Y-%m-%d') 
                for x in range(days)]
        dates.reverse()
        
        # Pobierz dane aktywności
        activity_data = [
            len(jira.search_issues(
                f'assignee = {user} AND updated >= "{date}" AND updated < "{(datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")}"'
            ))
            for date in dates
        ]
        
        return jsonify({
            'labels': dates,
            'data': activity_data
        })
        
    except Exception as e:
        logger.error(f"Error getting activity data: {str(e)}")
        return jsonify({'error': 'Failed to get activity data'}), 500

@api_bp.route('/jira/projects', methods=['GET'])
@auth_required()
def get_jira_projects():
    """Get JIRA projects."""
    try:
        projects = get_jira_projects()
        return jsonify(projects)
    except Exception as e:
        logger.error(f"Error getting JIRA projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/projects/<project_key>')
@login_required
def get_project_details(project_key):
    """Pobiera szczegóły projektu."""
    try:
        logger.info(f"Getting details for project: {project_key}")
        
        # Sprawdź sesję
        if not current_user.is_authenticated:
            logger.error("User not authenticated")
            return jsonify({
                'status': 'error',
                'message': 'Użytkownik nie jest zalogowany'
            }), 401

        jira_service = JiraService()
        if not jira_service.is_connected:
            logger.error("JIRA service not connected")
            return jsonify({
                'status': 'error',
                'message': 'Nie można połączyć się z JIRA'
            }), 500

        # Pobierz projekt z JIRA
        project = jira_service.get_project(project_key)
        logger.info(f"Retrieved project data: {project}")
        
        if not project:
            logger.warning(f"Project {project_key} not found")
            return jsonify({
                'status': 'error',
                'message': f'Projekt {project_key} nie został znaleziony'
            }), 404

        # Pobierz dodatkowe statystyki
        try:
            issues_count = jira_service.count_project_issues(project_key)
            active_users = jira_service.get_project_users(project_key)
            last_update = jira_service.get_project_last_update(project_key)
            logger.info(f"Retrieved stats - issues: {issues_count}, users: {len(active_users)}")
        except Exception as e:
            logger.error(f"Error getting project stats: {str(e)}")
            issues_count = 0
            active_users = []
            last_update = None

        response_data = {
            'status': 'success',
            'key': project.key,
            'name': project.name,
            'description': getattr(project, 'description', ''),
            'issues_count': issues_count,
            'active_users': len(active_users),
            'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None
        }

        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error getting project details: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/roles', methods=['POST'])
@login_required
def create_role():
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] === Starting role creation ===")
    
    try:
        # Dodajmy więcej logowania
        logger.info(f"[{request_id}] Request data: {request.get_data(as_text=True)}")
        logger.info(f"[{request_id}] Content-Type: {request.content_type}")
        logger.info(f"[{request_id}] User: {current_user.email}")
        logger.info(f"[{request_id}] Is admin: {current_user.is_admin}")

        # 1. Sprawdzenie uprawnień
        if not current_user.is_admin:
            logger.warning(f"[{request_id}] Access denied for user {current_user.email}")
            return jsonify({
                'status': 'error',
                'message': 'Brak uprawnień administratora'
            }), 403

        # 2. Walidacja formatu
        if not request.is_json:
            logger.error(f"[{request_id}] Invalid content type: {request.content_type}")
            return jsonify({
                'status': 'error',
                'message': 'Wymagany format JSON'
            }), 400

        # 3. Pobranie i walidacja danych
        data = request.get_json()
        logger.info(f"[{request_id}] Received data: {data}")

        if not data or not data.get('name'):
            logger.warning(f"[{request_id}] Missing required data")
            return jsonify({
                'status': 'error',
                'message': 'Nazwa roli jest wymagana'
            }), 400

        # 4. Sprawdzenie duplikatu
        existing_role = Role.query.filter_by(name=data['name']).first()
        if existing_role:
            logger.warning(f"[{request_id}] Role {data['name']} already exists")
            return jsonify({
                'status': 'error',
                'message': 'Rola o tej nazwie już istnieje'
            }), 400

        # 5. Tworzenie roli
        try:
            new_role = Role(
                name=data['name'],
                description=data.get('description', ''),
                permissions=data.get('permissions', [])
            )
            
            db.session.add(new_role)
            db.session.commit()
            
            logger.info(f"[{request_id}] Successfully created role: {new_role.name}")

            # 6. Przygotowanie odpowiedzi
            response_data = {
                'status': 'success',
                'message': f'Utworzono rolę {new_role.name}',
                'role': new_role.to_dict()
            }
            
            logger.info(f"[{request_id}] Sending response: {response_data}")
            return jsonify(response_data), 201

        except Exception as db_error:
            db.session.rollback()
            logger.error(f"[{request_id}] Database error: {str(db_error)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Błąd podczas zapisywania roli',
                'details': str(db_error)
            }), 500

    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Wystąpił nieoczekiwany błąd',
            'details': str(e)
        }), 500

@api_bp.route('/roles/<int:role_id>', methods=['GET'])
@admin_required
def get_role(role_id):
    """Pobieranie szczegółów roli."""
    try:
        role = Role.query.get_or_404(role_id)
        return jsonify({
            'status': 'success',
            'role': role.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting role {role_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/roles/<int:role_id>', methods=['PUT'])
@admin_required
def update_role(role_id):
    """Aktualizacja roli."""
    try:
        role = Role.query.get_or_404(role_id)
        data = request.get_json()
        
        if 'name' in data:
            # Sprawdź czy nazwa nie jest już zajęta
            existing_role = Role.query.filter_by(name=data['name']).first()
            if existing_role and existing_role.id != role_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Rola o tej nazwie już istnieje'
                }), 400
            role.name = data['name']
            
        if 'description' in data:
            role.description = data['description']
            
        if 'permissions' in data:
            role.permissions = data['permissions']
            
        db.session.commit()
        logger.info(f"Updated role: {role.name}")
        
        return jsonify({
            'status': 'success',
            'message': f'Zaktualizowano rolę {role.name}',
            'role': role.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating role {role_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@admin_required
def delete_role(role_id):
    """Usuwanie roli."""
    try:
        role = Role.query.get_or_404(role_id)
        
        # Nie pozwól usunąć ról systemowych
        if role.name in ['superadmin', 'admin', 'user']:
            return jsonify({
                'status': 'error',
                'message': 'Nie można usunąć roli systemowej'
            }), 400
            
        db.session.delete(role)
        db.session.commit()
        logger.info(f"Deleted role: {role.name}")
        
        return jsonify({
            'status': 'success',
            'message': f'Usunięto rolę {role.name}'
        })
        
    except Exception as e:
        logger.error(f"Error deleting role {role_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] === Starting user update ===")
    
    try:
        # 1. Pobierz użytkownika
        user = User.query.get_or_404(user_id)
        logger.info(f"[{request_id}] Updating user: {user.email}")

        # 2. Pobierz dane
        data = request.get_json()
        logger.info(f"[{request_id}] Update data: {data}")

        # 3. Aktualizuj dane
        if 'email' in data:
            # Sprawdź czy email nie jest zajęty
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Email jest już zajęty'
                }), 400
            user.email = data['email']

        if 'first_name' in data:
            user.first_name = data['first_name']

        if 'last_name' in data:
            user.last_name = data['last_name']

        if 'roles' in data:
            # Pobierz role
            roles = Role.query.filter(Role.id.in_(data['roles'])).all()
            if not roles:
                return jsonify({
                    'status': 'error',
                    'message': 'Nie znaleziono wybranych ról'
                }), 400
            user.roles = roles

        if 'is_active' in data:
            user.is_active = data['is_active']

        # 4. Zapisz zmiany
        try:
            db.session.commit()
            logger.info(f"[{request_id}] User updated successfully")
            
            return jsonify({
                'status': 'success',
                'message': 'Zaktualizowano użytkownika',
                'user': user.to_dict()
            })

        except Exception as db_error:
            db.session.rollback()
            logger.error(f"[{request_id}] Database error: {str(db_error)}")
            return jsonify({
                'status': 'error',
                'message': 'Błąd podczas zapisywania zmian',
                'details': str(db_error)
            }), 500

    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Wystąpił nieoczekiwany błąd',
            'details': str(e)
        }), 500

@api_bp.route('/teams')
@login_required
def get_teams():
    """Get all teams with member count."""
    try:
        teams = Team.query.all()
        return jsonify([{
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'members_count': len(team.members),
            'created_at': team.created_at.isoformat() if team.created_at else None,
            'updated_at': team.updated_at.isoformat() if team.updated_at else None
        } for team in teams])
    except Exception as e:
        logger.error(f"Error getting teams: {str(e)}")
        return jsonify({"error": "Failed to get teams"}), 500

@api_bp.route('/reports/workload', methods=['GET'])
def get_workload():
    """Get workload report data."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        
        data = get_workload_report(start_date, end_date)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/log-error', methods=['POST'])
@csrf.exempt  # Only if you want to exempt this route from CSRF protection
def log_error():
    """Endpoint for client-side error logging"""
    try:
        error_data = request.get_json()
        # Log the error
        current_app.logger.error(f"Client-side error: {error_data}")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        current_app.logger.error(f"Error logging client error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.before_request
def before_request():
    """Add CORS headers to API responses."""
    if request.method == 'OPTIONS':
        response = current_app.make_default_options_response()
    else:
        response = make_response()
    
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@api_bp.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@api_bp.route('/users')
@auth_required(['admin'])
def get_users():
    """Get all users."""
    try:
        users = User.query.all()
        # Nawet gdy users jest pustą listą, jsonify([]) zwróci "[]"
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'roles': [role.name for role in user.roles],
            'is_active': user.is_active
        } for user in users])
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 