def test_role_list(client, admin_user):
    """Test role listing page."""
    response = client.get('/admin/roles')
    assert response.status_code == 200
    assert b'Role Management' in response.data

def test_role_api(client, admin_user):
    """Test role API endpoint."""
    response = client.get('/api/admin/roles')
    assert response.status_code == 200
    data = response.json
    assert 'data' in data
    assert 'recordsTotal' in data 