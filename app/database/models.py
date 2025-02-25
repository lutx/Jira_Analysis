"""
This module is deprecated. Use models from app.models package instead.
All models have been moved to app/models/ directory.
"""

from app.models import (
    User, Role, UserRole,
    Portfolio, PortfolioProject,
    Worklog, LeaveRequest,
    TokenBlocklist
)

__all__ = [
    'User', 'Role', 'UserRole',
    'Portfolio', 'PortfolioProject',
    'Worklog', 'LeaveRequest',
    'TokenBlocklist'
]

# Usuń wszystkie definicje klas poniżej tego komentarza 