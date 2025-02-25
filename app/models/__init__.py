"""
Models package initialization.
Import order matters to prevent circular dependencies.
"""
from app.extensions import db

# Core models with no dependencies
from .role import Role
from .user_role import UserRole  # Junction table first
from .user import User
from .team import Team
from .project import Project
from .worklog import Worklog
from .issue import Issue
from .jira_config import JiraConfig
from .setting import Setting
from .token_blocklist import TokenBlocklist
from .project_assignment import ProjectAssignment
from .portfolio import Portfolio, portfolio_projects
from .leave import Leave
from .team_membership import TeamMembership
from .user_availability import UserAvailability
from .leave_request import LeaveRequest

# Export only what's necessary
__all__ = [
    'User',
    'Role',
    'Project',
    'Portfolio',
    'portfolio_projects',
    'Team',
    'Worklog',
    'ProjectAssignment',
    'TeamMembership'
] 