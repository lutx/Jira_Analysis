import os
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def verify_templates():
    """Verify that all required templates exist."""
    template_dir = os.path.join(current_app.root_path, 'templates')
    required_templates = [
        # Admin Dashboard
        'admin/dashboard/index.html',
        
        # Reports
        'admin/reports/overview.html',
        'admin/reports/workload.html',
        'admin/reports/efficiency.html',
        'admin/reports/productivity.html',
        'admin/reports/capacity.html',
        'admin/reports/utilization.html',
        'admin/reports/cost.html',
        'admin/reports/time_tracking.html',
        'admin/reports/shadow_work.html',
        
        # User Management
        'admin/users/index.html',
        'admin/roles/index.html',
        'admin/teams/index.html',
        
        # Project Management
        'admin/projects/index.html',
        'admin/portfolios/index.html',
        'admin/portfolios/assignments.html',
        'admin/portfolios/analysis.html',
        
        # Time Management
        'admin/leave_management/index.html',
        'admin/worklogs/index.html',
        'admin/availability/index.html',
        
        # Administration
        'admin/administration/index.html',
        'admin/administration/system_settings.html',
        'admin/administration/jira_settings.html',
        'admin/administration/email_settings.html',
        'admin/administration/system_health.html',
        'admin/administration/system_logs.html',
        'admin/administration/audit.html',
        'admin/administration/backup.html',
        
        # Modals
        'admin/modals/user_form.html',
        'admin/modals/role_form.html',
        'admin/modals/team_form.html',
        'admin/modals/project_form.html',
        'admin/modals/portfolio_form.html',
        'admin/modals/worklog_form.html',
        'admin/modals/leave_request_form.html',
        
        # Error Pages
        'errors/403.html',
        'errors/404.html',
        'errors/500.html',
        'errors/error.html'
    ]
    
    missing_templates = []
    for template in required_templates:
        template_path = os.path.join(template_dir, template)
        if not os.path.exists(template_path):
            missing_templates.append(template)
            logger.warning(f"Missing template: {template}")
            
    return missing_templates 