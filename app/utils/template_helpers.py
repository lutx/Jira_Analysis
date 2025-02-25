from flask import current_app
from flask_login import current_user

def get_menu_items():
    """Get menu items based on user permissions."""
    menu_items = [
        {
            'name': 'Dashboard',
            'url': '/dashboard',
            'icon': 'fas fa-tachometer-alt',
            'required_permissions': ['read']
        },
        {
            'name': 'Teams',
            'url': '/teams',
            'icon': 'fas fa-users',
            'required_permissions': ['read', 'manage_teams']
        },
        {
            'name': 'Projects',
            'url': '/projects',
            'icon': 'fas fa-project-diagram',
            'required_permissions': ['read', 'manage_projects']
        },
        {
            'name': 'Users',
            'url': '/users',
            'icon': 'fas fa-user',
            'required_permissions': ['read', 'manage_users']
        },
        {
            'name': 'Settings',
            'url': '/settings',
            'icon': 'fas fa-cog',
            'required_permissions': ['manage_settings']
        },
        {
            'name': 'Reports',
            'url': '/reports',
            'icon': 'fas fa-chart-bar',
            'required_permissions': ['view_reports']
        }
    ]

    if not current_user.is_authenticated:
        return []

    # Filter menu items based on user permissions
    return [
        item for item in menu_items
        if current_user.has_any_permission(item['required_permissions'])
    ] 