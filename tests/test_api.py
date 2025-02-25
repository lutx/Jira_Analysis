import pytest
from flask import url_for

def test_get_roles_api(client, admin_user, auth_headers):
    """Test getting roles through API."""
    # Create test roles first
    from app.models import Role
    role1 = Role(name="Test Role 1", description="Test Description 1")
    role2 = Role(name="Test Role 2", description="Test Description 2")
    db.session.add_all([role1, role2])
    db.session.commit()

    response = client.get(
        url_for('api.get_roles'),
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json
    
    assert 'data' in data
    assert 'recordsTotal' in data
    assert data['recordsTotal'] >= 2
    
    # Check if our test roles are in the response
    role_names = [role['name'] for role in data['data']]
    assert "Test Role 1" in role_names
    assert "Test Role 2" in role_names

def test_get_roles_api_search(client, admin_user, auth_headers):
    """Test searching roles through API."""
    response = client.get(
        url_for('api.get_roles') + '?search[value]=Test',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json
    
    # All returned roles should contain "Test" in their name
    assert all('Test' in role['name'] for role in data['data']) 