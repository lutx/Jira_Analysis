import pytest
from flask import url_for
from app.middleware.access_control import check_project_access, check_team_access

def test_project_access(client, auth):
    # Test unauthorized access
    response = client.get(url_for('views.project_details', project_id=1))
    assert response.status_code == 302  # Redirect to login
    
    # Login and test access to non-existent project
    auth.login()
    response = client.get(url_for('views.project_details', project_id=9999))
    assert response.status_code == 404
    
    # Test access to unauthorized project
    response = client.get(url_for('views.project_details', project_id=1))
    assert response.status_code == 302  # Redirect to dashboard
    assert b'You do not have access to this project' in response.data

def test_team_access(client, auth):
    # Test unauthorized access
    response = client.get(url_for('views.team_details', team_id=1))
    assert response.status_code == 302  # Redirect to login
    
    # Login and test access to non-existent team
    auth.login()
    response = client.get(url_for('views.team_details', team_id=9999))
    assert response.status_code == 404
    
    # Test access to unauthorized team
    response = client.get(url_for('views.team_details', team_id=1))
    assert response.status_code == 302  # Redirect to dashboard
    assert b'You do not have access to this team' in response.data 