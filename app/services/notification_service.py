from typing import List, Dict
from datetime import datetime

def get_admin_notifications() -> List[Dict]:
    """Get notifications for admin dashboard."""
    notifications = []
    
    # Sprawdź stan systemu
    system_health = get_system_health()
    if system_health['memory_usage'] > 90:
        notifications.append({
            'type': 'warning',
            'message': 'High memory usage detected'
        })
    
    # Sprawdź synchronizację z JIRA
    jira_config = JiraConfig.query.filter_by(is_active=True).first()
    if jira_config and jira_config.last_sync:
        if (datetime.now() - jira_config.last_sync).days > 1:
            notifications.append({
                'type': 'info',
                'message': 'JIRA synchronization is outdated'
            })
    
    return notifications 