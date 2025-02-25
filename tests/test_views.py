import pytest
from flask import url_for
from app.models import User, Project, Team, Worklog

def test_dashboard_view(client, auth):
    """Test dashboard view."""
    auth.login()
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Dashboard' in response.data

def test_profile_view(client, auth):
    """Test profile view."""
    auth.login()
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Profil' in response.data

def test_settings_view(client, auth):
    """Test settings view."""
    auth.login()
    response = client.get('/settings')
    assert response.status_code == 200
    assert b'Ustawienia' in response.data

def test_project_details_view(client, auth):
    auth.login()
    
    # Test non-existent project
    response = client.get(url_for('views.project_details', project_id=9999))
    assert response.status_code == 404
    
    # Test unauthorized project access
    response = client.get(url_for('views.project_details', project_id=1))
    assert response.status_code == 302
    assert b'You do not have access to this project' in response.data

def test_team_details_view(client, auth):
    auth.login()
    
    # Test non-existent team
    response = client.get(url_for('views.team_details', team_id=9999))
    assert response.status_code == 404 