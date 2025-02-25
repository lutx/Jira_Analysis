def test_csrf_protection(client):
    """Test ochrony CSRF."""
    # Test bez tokenu CSRF
    response = client.post('/api/teams/1/export/workload')
    assert response.status_code == 400
    assert 'CSRF token' in response.json['message']
    
    # Test z poprawnym tokenem
    response = client.get('/api/csrf-token')
    csrf_token = response.json['csrf_token']
    
    headers = {'X-CSRF-Token': csrf_token}
    response = client.post('/api/teams/1/export/workload', headers=headers)
    assert response.status_code != 400 