from app.models import Project, ProjectAssignment, User, Role
from app.extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProjectService:
    @staticmethod
    def get_project_assignments(project_id: int, date: datetime = None):
        """Pobiera przypisania do projektu."""
        query = ProjectAssignment.query.filter_by(project_id=project_id)
        
        if date:
            query = query.filter(
                ProjectAssignment.start_date <= date,
                (ProjectAssignment.end_date >= date) | (ProjectAssignment.end_date.is_(None))
            )
            
        return query.all()

    @staticmethod
    def get_project_workload(project_id: int, start_date: datetime, end_date: datetime):
        """Pobiera obciążenie projektu w danym okresie."""
        from app.models import Worklog
        
        workload = db.session.query(
            User.username,
            Role.name.label('role'),
            db.func.sum(Worklog.hours).label('total_hours')
        ).join(
            ProjectAssignment, ProjectAssignment.user_id == User.id
        ).join(
            Role, Role.id == ProjectAssignment.role_id
        ).join(
            Worklog, Worklog.user_id == User.id
        ).filter(
            ProjectAssignment.project_id == project_id,
            Worklog.date.between(start_date, end_date)
        ).group_by(
            User.username,
            Role.name
        ).all()
        
        return workload

    @staticmethod
    def assign_user_to_project(user_id: int, project_id: int, role_id: int, 
                             planned_hours: float, start_date: datetime, 
                             end_date: datetime = None):
        """Przypisuje użytkownika do projektu."""
        try:
            assignment = ProjectAssignment(
                user_id=user_id,
                project_id=project_id,
                role_id=role_id,
                planned_hours=planned_hours,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(assignment)
            db.session.commit()
            return assignment
        except Exception as e:
            logger.error(f"Error assigning user to project: {str(e)}")
            db.session.rollback()
            raise 