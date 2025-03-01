from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.models.worklog import Worklog
from app.database import get_db
import logging
from calendar import monthrange
from flask import current_app
from app.extensions import db
from app.models.user import User
from app.models.project import Project
from app.models.role import Role
from app.models.project_assignment import ProjectAssignment
from app.models.team import Team
from app.models.team_membership import TeamMembership as TeamMember
from sqlalchemy import func, and_, or_
from app.utils.date_helpers import get_date_range
from app.cache import cache
from app.monitoring import monitor, Monitor
from app.exceptions import (
    AppError, ValidationError, ExportError, DatabaseError,
    ResourceNotFoundError, BusinessLogicError, ReportError
)
from app.models import Report, ReportResult, Leave, Portfolio

logger = logging.getLogger(__name__)

class ReportService:
    @staticmethod
    def generate_activity_report(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generuje raport aktywności użytkowników."""
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT 
                    user_name,
                    DATE(work_date) as date,
                    SUM(time_spent) as hours,
                    COUNT(DISTINCT issue_key) as tasks
                FROM worklogs
                WHERE work_date BETWEEN ? AND ?
                GROUP BY user_name, DATE(work_date)
                ORDER BY user_name, date
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            results = cursor.fetchall()
            
            report = {
                'daily_activity': {},
                'user_summary': {},
                'total_hours': 0,
                'total_tasks': 0
            }
            
            for row in results:
                user = row['user_name']
                date = row['date']
                hours = row['hours']
                tasks = row['tasks']
                
                # Daily activity
                if date not in report['daily_activity']:
                    report['daily_activity'][date] = {
                        'total_hours': 0,
                        'users': {}
                    }
                
                report['daily_activity'][date]['total_hours'] += hours
                report['daily_activity'][date]['users'][user] = {
                    'hours': hours,
                    'tasks': tasks
                }
                
                # User summary
                if user not in report['user_summary']:
                    report['user_summary'][user] = {
                        'total_hours': 0,
                        'total_tasks': 0,
                        'avg_daily_hours': 0
                    }
                
                report['user_summary'][user]['total_hours'] += hours
                report['user_summary'][user]['total_tasks'] += tasks
                
                # Global totals
                report['total_hours'] += hours
                report['total_tasks'] += tasks
            
            # Calculate averages
            days = (end_date - start_date).days + 1
            for user in report['user_summary']:
                report['user_summary'][user]['avg_daily_hours'] = \
                    report['user_summary'][user]['total_hours'] / days
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating activity report: {str(e)}")
            raise

    @staticmethod
    def generate_project_report(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generuje raport projektów."""
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT 
                    project_key,
                    user_name,
                    SUM(time_spent) as hours,
                    COUNT(DISTINCT issue_key) as tasks
                FROM worklogs
                WHERE work_date BETWEEN ? AND ?
                GROUP BY project_key, user_name
                ORDER BY project_key, hours DESC
            """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            results = cursor.fetchall()
            
            report = {
                'projects': {},
                'total_hours': 0,
                'total_tasks': 0
            }
            
            for row in results:
                project = row['project_key']
                user = row['user_name']
                hours = row['hours']
                tasks = row['tasks']
                
                if project not in report['projects']:
                    report['projects'][project] = {
                        'total_hours': 0,
                        'total_tasks': 0,
                        'users': {}
                    }
                
                report['projects'][project]['total_hours'] += hours
                report['projects'][project]['total_tasks'] += tasks
                report['projects'][project]['users'][user] = {
                    'hours': hours,
                    'tasks': tasks
                }
                
                report['total_hours'] += hours
                report['total_tasks'] += tasks
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating project report: {str(e)}")
            raise

    @staticmethod
    def get_workload_report(start_date: str, end_date: str, 
                           user_name: Optional[str] = None, 
                           project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pobierz raport obciążenia pracą."""
        try:
            db = get_db()
            
            query = '''
                SELECT 
                    u.username,
                    w.project_key,
                    r.name as role_name,
                    pa.planned_hours,
                    SUM(w.time_spent) as total_time,
                    COUNT(DISTINCT w.issue_key) as issues_count,
                    (pa.planned_hours * 3600 - SUM(w.time_spent)) as difference
                FROM users u
                JOIN worklogs w ON u.id = w.user_id
                JOIN project_assignments pa ON u.id = pa.user_id 
                    AND w.project_key = pa.project_key
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN roles r ON ur.role_name = r.name
                WHERE w.started BETWEEN ? AND ?
            '''
            
            params = [start_date, end_date]
            
            if user_name:
                query += ' AND u.username = ?'
                params.append(user_name)
            
            if project_key:
                query += ' AND w.project_key = ?'
                params.append(project_key)
            
            query += ' GROUP BY u.username, w.project_key, r.name'
            
            results = db.execute(query, params).fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting workload report: {str(e)}")
            return []

    @staticmethod
    def get_role_distribution_report(start_date: str, end_date: str, portfolio_id: int = None) -> List[Dict[str, Any]]:
        """Generuje raport rozkładu pracy według ról."""
        try:
            query = db.session.query(
                Role.name,
                db.func.sum(Worklog.hours).label('total_hours')
            ).join(
                ProjectAssignment, ProjectAssignment.role_id == Role.id
            ).join(
                Worklog, Worklog.user_id == ProjectAssignment.user_id
            )
            
            if portfolio_id:
                query = query.join(
                    Project, Project.id == ProjectAssignment.project_id
                ).filter(Project.portfolio_id == portfolio_id)
                
            if start_date and end_date:
                query = query.filter(Worklog.date.between(start_date, end_date))
                
            results = query.group_by(Role.name).all()
            
            return {
                'labels': [r[0] for r in results],
                'data': [float(r[1]) for r in results]
            }
            
            results = db.execute(query, params).fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error generating role distribution report: {str(e)}")
            raise

    @staticmethod
    def get_shadow_work_report(month_year: str) -> List[Dict[str, Any]]:
        """Generuje raport pracy poza przypisaniami."""
        try:
            date = datetime.strptime(month_year, '%Y-%m')
            next_month = date.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            
            shadow_work = db.session.query(
                User.username,
                Project.name.label('project'),
                db.func.sum(Worklog.hours).label('hours')
            ).join(
                Worklog, Worklog.user_id == User.id
            ).join(
                Project, Project.id == Worklog.project_id
            ).outerjoin(
                ProjectAssignment,
                db.and_(
                    ProjectAssignment.user_id == User.id,
                    ProjectAssignment.project_id == Project.id,
                    ProjectAssignment.start_date <= date,
                    db.or_(
                        ProjectAssignment.end_date.is_(None),
                        ProjectAssignment.end_date >= next_month
                    )
                )
            ).filter(
                ProjectAssignment.id.is_(None),
                Worklog.date.between(date, next_month - timedelta(days=1))
            ).group_by(
                User.username,
                Project.name
            ).all()
            
            return {
                'month_year': month_year,
                'data': [{
                    'username': sw[0],
                    'project': sw[1],
                    'hours': float(sw[2])
                } for sw in shadow_work]
            }
            
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error generating shadow work report: {str(e)}")
            raise

    @staticmethod
    def get_availability_report(month_year: str) -> List[Dict[str, Any]]:
        """Pobierz raport dostępności użytkowników."""
        try:
            db = get_db()
            
            results = db.execute('''
                SELECT 
                    u.username,
                    ua.working_days,
                    ua.leave_days,
                    ua.holidays,
                    ua.total_capacity,
                    COALESCE(pa.total_planned, 0) as total_planned,
                    COALESCE(w.total_actual, 0) as total_actual
                FROM users u
                JOIN user_availability ua ON u.id = ua.user_id
                LEFT JOIN (
                    SELECT user_id, SUM(planned_hours) as total_planned
                    FROM project_assignments
                    WHERE month_year = ?
                    GROUP BY user_id
                ) pa ON u.id = pa.user_id
                LEFT JOIN (
                    SELECT user_id, SUM(time_spent) as total_actual
                    FROM worklogs
                    WHERE strftime('%Y-%m', started) = ?
                    GROUP BY user_id
                ) w ON u.id = w.user_id
                WHERE ua.month_year = ?
                ORDER BY u.username
            ''', (month_year, month_year, month_year)).fetchall()
            
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error getting availability report: {str(e)}")
            return []

    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        """Pobierz listę wszystkich użytkowników."""
        try:
            db = get_db()
            users = db.execute('''
                SELECT id, username, email 
                FROM users 
                WHERE is_active = 1 
                ORDER BY username
            ''').fetchall()
            return [dict(user) for user in users]
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return []

    @staticmethod
    def get_all_portfolios() -> List[Dict[str, Any]]:
        """Pobierz listę wszystkich portfolii."""
        try:
            db = get_db()
            portfolios = db.execute('''
                SELECT id, name 
                FROM portfolios 
                WHERE status = 'active' 
                ORDER BY name
            ''').fetchall()
            return [dict(portfolio) for portfolio in portfolios]
        except Exception as e:
            logger.error(f"Error getting portfolios: {str(e)}")
            return []

def generate_report(report_type: str, **kwargs):
    """Funkcja pomocnicza do generowania raportów."""
    try:
        if report_type == 'activity':
            return ReportService.generate_activity_report(**kwargs)
        elif report_type == 'role_distribution':
            return ReportService.get_role_distribution_report(**kwargs)
        elif report_type == 'shadow_work':
            return ReportService.get_shadow_work_report(**kwargs)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    except Exception as e:
        logger.error(f"Error generating {report_type} report: {str(e)}")
        raise

def get_project_assignments(project_id: int) -> Dict[str, Any]:
    """Get project assignments."""
    try:
        # Get project and its assignments
        with db.session() as session:
            # Get roles
            roles = Role.query.all()
            if not roles:
                raise ResourceNotFoundError(
                    "No roles found",
                    {'entity': 'Role'}
                )
                
            roles_dict = {role.id: role.name for role in roles}
            
            # Get assignments
            assignments = (
                db.session.query(ProjectAssignment, Role)
                .join(Role)
                .filter(ProjectAssignment.project_id == project_id)
                .all()
            )
            
            # Get project details
            project = (
                db.session.query(Project)
                .join(ProjectAssignment)
                .filter(Project.id == project_id)
                .first()
            )
            
            if not project:
                raise ResourceNotFoundError(
                    f"Project {project_id} not found",
                    {
                        'entity': 'Project',
                        'project_id': project_id
                    }
                )
            
            # Format assignments by role
            assignments_by_role = {}
            for assignment, role in assignments:
                if role.name not in assignments_by_role:
                    assignments_by_role[role.name] = []
                assignments_by_role[role.name].append(assignment)
            
            # Get role statistics
            role_stats = {}
            for role in roles:
                role_stats[role.name] = {
                    'count': len([a for a in assignments if a[1].id == role.id]),
                    'required': project.get_required_role_count(role.name)
                }
            
            return {
                'assignments': assignments_by_role,
                'role_stats': role_stats,
                'total_count': len(assignments)
            }
            
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Error getting project assignments: {str(e)}")
        raise DatabaseError(
            "Error getting project assignments",
            {
                'error': str(e),
                'project_id': project_id
            }
        )

def update_project_assignments(project_id: int, assignments_data: List[Dict[str, Any]]) -> bool:
    """Update project assignments."""
    try:
        with db.session.begin():
            # Get current assignments
            current_assignments = (
                db.session.query(User, Project)
                .join(ProjectAssignment)
                .filter(Project.id == project_id)
                .all()
            )
            
            # Get project
            project = Project.query.get(project_id)
            if not project:
                logger.error(f"Project {project_id} not found")
                return False
            
            # Create new assignments
            for assignment in assignments_data:
                new_assignment = ProjectAssignment(
                    project_id=project_id,
                    user_id=assignment['user_id'],
                    role_id=assignment['role_id']
                )
                db.session.add(new_assignment)
            
            # Get assignments to remove
            assignments_to_remove = (
                db.session.query(ProjectAssignment)
                .join(User)
                .join(Project)
                .filter(
                    ProjectAssignment.project_id == project_id,
                    ProjectAssignment.user_id.notin_([a['user_id'] for a in assignments_data])
                )
                .all()
            )
            
            # Remove old assignments
            for assignment in assignments_to_remove:
                db.session.delete(assignment)
            
            return True
            
    except Exception as e:
        logger.error(f"Error updating project assignments: {str(e)}")
        db.session.rollback()
        return False

def get_user_assignments(user_id: int) -> List[Dict[str, Any]]:
    """Get user project assignments."""
    try:
        assignments = (
            ProjectAssignment.query
            .join(User)
            .filter(User.id == user_id)
            .all()
        )
        
        return [assignment.to_dict() for assignment in assignments]
        
    except Exception as e:
        logger.error(f"Error getting user assignments: {str(e)}")
        return []

def get_project_roles(project_id: int) -> List[Dict[str, Any]]:
    """Get project roles."""
    try:
        roles = (
            Role.query
            .join(ProjectAssignment)
            .filter(ProjectAssignment.project_id == project_id)
            .distinct()
            .all()
        )
        
        return [role.to_dict() for role in roles]
        
    except Exception as e:
        logger.error(f"Error getting project roles: {str(e)}")
        return []

def analyze_role_distribution():
    """Analyze role distribution across users."""
    roles = Role.query.all()
    data = []
    
    for role in roles:
        user_count = len(role.users)
        data.append({
            'role': role.name,
            'user_count': user_count,
            'percentage': round((user_count / User.query.count()) * 100, 2) if User.query.count() > 0 else 0
        })
    
    return {
        'labels': [d['role'] for d in data],
        'data': [d['user_count'] for d in data],
        'percentages': [d['percentage'] for d in data]
    }

def analyze_shadow_work():
    """Analyze shadow work (work without JIRA tickets)."""
    # Pobierz dane z ostatnich 30 dni
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Wszystkie worklog'i
    total_worklogs = Worklog.query.filter(
        Worklog.work_date.between(start_date, end_date)
    ).count()
    
    # Worklog'i bez powiązanych JIRA issues
    shadow_worklogs = Worklog.query.join(
        Worklog.issue
    ).filter(
        Worklog.work_date.between(start_date, end_date),
        Worklog.issue.has(jira_key=None)
    ).count()
    
    shadow_percentage = round((shadow_worklogs / total_worklogs) * 100, 2) if total_worklogs > 0 else 0
    
    return {
        'total_worklogs': total_worklogs,
        'shadow_worklogs': shadow_worklogs,
        'shadow_percentage': shadow_percentage,
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
    }

def get_workload_report(start_date=None, end_date=None, format='json'):
    """Generate workload report."""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        workload_data = db.session.query(
            User.id,
            User.username,
            func.sum(Worklog.time_spent).label('total_time')
        ).join(
            Worklog
        ).filter(
            Worklog.work_date.between(start_date, end_date)
        ).group_by(
            User.id
        ).all()
        
        data = [{
            'user_id': data[0],
            'username': data[1],
            'total_hours': round(data[2] / 3600, 2) if data[2] else 0
        } for data in workload_data]
        
        if format == 'csv':
            try:
                return export_to_csv(data)
            except Exception as e:
                raise ExportError(f"Failed to export report to CSV: {str(e)}")
        elif format == 'excel':
            try:
                return export_to_excel(data)
            except Exception as e:
                raise ExportError(f"Failed to export report to Excel: {str(e)}")
        return data
    except ValidationError:
        raise
    except Exception as e:
        raise ReportError(f"Failed to generate workload report: {str(e)}")

def generate_report(report: Report) -> Optional[ReportResult]:
    """Generate report based on type and parameters."""
    try:
        result = ReportResult(
            report_id=report.id,
            status='running'
        )
        db.session.add(result)
        db.session.commit()

        params = report.get_parameters()
        report_data = None

        if report.report_type == 'leave_usage':
            report_data = generate_leave_usage_report(params)
        elif report.report_type == 'team_availability':
            report_data = generate_team_availability_report(params)
        elif report.report_type == 'cost_tracking':
            report_data = generate_cost_tracking_report(params)
        elif report.report_type == 'project_allocation':
            report_data = generate_project_allocation_report(params)
        else:
            result.set_error(f"Unknown report type: {report.report_type}")
            db.session.commit()
            return result

        result.set_result(report_data)
        db.session.commit()
        return result

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        if result:
            result.set_error(str(e))
            db.session.commit()
        return None

def generate_leave_usage_report(params: Dict) -> Dict:
    """Generate leave usage report."""
    try:
        start_date = datetime.strptime(params.get('start_date', ''), '%Y-%m-%d') if params.get('start_date') else None
        end_date = datetime.strptime(params.get('end_date', ''), '%Y-%m-%d') if params.get('end_date') else None
        team_id = params.get('team_id')

        query = db.session.query(
            Leave.user_id,
            Leave.leave_type,
            func.sum(Leave.duration).label('total_days')
        ).filter(Leave.status == 'approved')

        if start_date:
            query = query.filter(Leave.start_date >= start_date)
        if end_date:
            query = query.filter(Leave.end_date <= end_date)
        if team_id:
            query = query.join(User).filter(User.team_id == team_id)

        results = query.group_by(Leave.user_id, Leave.leave_type).all()

        # Process results
        leave_usage = {}
        for user_id, leave_type, total_days in results:
            user = User.query.get(user_id)
            if user:
                if user.username not in leave_usage:
                    leave_usage[user.username] = {}
                leave_usage[user.username][leave_type] = float(total_days)

        return {
            'leave_usage': leave_usage,
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error generating leave usage report: {str(e)}")
        raise

def generate_team_availability_report(params: Dict) -> Dict:
    """Generate team availability report."""
    try:
        start_date = datetime.strptime(params.get('start_date', ''), '%Y-%m-%d') if params.get('start_date') else None
        end_date = datetime.strptime(params.get('end_date', ''), '%Y-%m-%d') if params.get('end_date') else None
        team_id = params.get('team_id')

        # Get all approved leaves in the period
        leaves_query = Leave.query.filter(Leave.status == 'approved')
        if start_date:
            leaves_query = leaves_query.filter(Leave.end_date >= start_date)
        if end_date:
            leaves_query = leaves_query.filter(Leave.start_date <= end_date)

        # Get team members
        team_members = User.query.filter_by(team_id=team_id).all() if team_id else User.query.all()

        availability = {}
        for user in team_members:
            user_leaves = leaves_query.filter(Leave.user_id == user.id).all()
            
            # Calculate availability
            total_days = (end_date - start_date).days + 1 if start_date and end_date else 0
            leave_days = sum(leave.duration for leave in user_leaves)
            
            availability[user.username] = {
                'total_days': total_days,
                'leave_days': leave_days,
                'available_days': total_days - leave_days,
                'availability_percentage': ((total_days - leave_days) / total_days * 100) if total_days > 0 else 100
            }

        return {
            'team_availability': availability,
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error generating team availability report: {str(e)}")
        raise

def generate_cost_tracking_report(params: Dict) -> Dict:
    """Generate cost tracking report based on role hourly rates."""
    try:
        start_date = datetime.strptime(params.get('start_date', ''), '%Y-%m-%d') if params.get('start_date') else None
        end_date = datetime.strptime(params.get('end_date', ''), '%Y-%m-%d') if params.get('end_date') else None
        project_id = params.get('project_id')

        from app.models.worklog import Worklog
        from app.models.user_role import UserRole

        # Get worklogs with role information
        query = db.session.query(
            Worklog.project_id,
            Role.name.label('role_name'),
            Role.hourly_rate,
            func.sum(Worklog.hours_spent).label('total_hours')
        ).join(
            UserRole, UserRole.user_id == Worklog.user_id
        ).join(
            Role, Role.id == UserRole.role_id
        )

        if start_date:
            query = query.filter(Worklog.date >= start_date)
        if end_date:
            query = query.filter(Worklog.date <= end_date)
        if project_id:
            query = query.filter(Worklog.project_id == project_id)

        results = query.group_by(
            Worklog.project_id,
            Role.name,
            Role.hourly_rate
        ).all()

        # Process results
        cost_tracking = {}
        for project_id, role_name, hourly_rate, total_hours in results:
            project = Project.query.get(project_id)
            if project:
                if project.name not in cost_tracking:
                    cost_tracking[project.name] = {
                        'total_cost': 0,
                        'roles': {}
                    }
                
                role_cost = float(hourly_rate) * float(total_hours)
                cost_tracking[project.name]['roles'][role_name] = {
                    'hours': float(total_hours),
                    'rate': float(hourly_rate),
                    'cost': role_cost
                }
                cost_tracking[project.name]['total_cost'] += role_cost

        return {
            'cost_tracking': cost_tracking,
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error generating cost tracking report: {str(e)}")
        raise

def generate_project_allocation_report(params: Dict) -> Dict:
    """Generate project allocation report."""
    try:
        start_date = datetime.strptime(params.get('start_date', ''), '%Y-%m-%d') if params.get('start_date') else None
        end_date = datetime.strptime(params.get('end_date', ''), '%Y-%m-%d') if params.get('end_date') else None
        portfolio_id = params.get('portfolio_id')

        from app.models.worklog import Worklog
        from app.models.project_assignment import ProjectAssignment

        # Get project assignments and actual work
        query = db.session.query(
            Project.id,
            Project.name,
            func.sum(ProjectAssignment.planned_hours).label('planned_hours'),
            func.sum(Worklog.hours_spent).label('actual_hours')
        ).outerjoin(
            ProjectAssignment, Project.id == ProjectAssignment.project_id
        ).outerjoin(
            Worklog, Project.id == Worklog.project_id
        )

        if portfolio_id:
            portfolio = Portfolio.query.get(portfolio_id)
            if portfolio:
                query = query.filter(Project.id.in_([p.id for p in portfolio.projects]))

        if start_date:
            query = query.filter(
                db.or_(
                    ProjectAssignment.start_date >= start_date,
                    Worklog.date >= start_date
                )
            )
        if end_date:
            query = query.filter(
                db.or_(
                    ProjectAssignment.end_date <= end_date,
                    Worklog.date <= end_date
                )
            )

        results = query.group_by(Project.id, Project.name).all()

        # Process results
        project_allocation = {}
        for project_id, project_name, planned_hours, actual_hours in results:
            planned = float(planned_hours) if planned_hours else 0
            actual = float(actual_hours) if actual_hours else 0
            
            project_allocation[project_name] = {
                'planned_hours': planned,
                'actual_hours': actual,
                'utilization': (actual / planned * 100) if planned > 0 else 0,
                'difference': actual - planned
            }

        return {
            'project_allocation': project_allocation,
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }

    except Exception as e:
        logger.error(f"Error generating project allocation report: {str(e)}")
        raise 