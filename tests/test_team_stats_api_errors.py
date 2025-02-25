def test_api_invalid_team_id(client, auth):
    """Test API dla nieprawidłowego ID zespołu."""
    auth.login()
    
    response = client.get('/api/teams/999999/members/user1/stats')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_api_unauthorized_access(client):
    """Test API bez autoryzacji."""
    response = client.get('/api/teams/1/members/user1/stats')
    assert response.status_code == 401

def test_api_invalid_date_format(client, auth, test_team):
    """Test API z nieprawidłowym formatem daty."""
    auth.login()
    
    response = client.get(
        f'/api/teams/{test_team.id}/members/user1/stats?start_date=invalid'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_api_invalid_export_format(client, auth, test_team):
    """Test API z nieprawidłowym formatem eksportu."""
    auth.login()
    
    response = client.get(
        f'/api/teams/{test_team.id}/members/user1/stats/export?format=invalid'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data 