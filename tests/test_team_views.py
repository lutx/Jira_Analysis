def test_member_stats_view(client, auth, test_team, test_user):
    """Test widoku statystyk członka zespołu."""
    auth.login()
    
    response = client.get(f'/teams/{test_team.id}/members/{test_user.user_name}/stats')
    assert response.status_code == 200
    assert b'Statystyki Członka Zespołu' in response.data
    assert bytes(test_user.user_name, 'utf-8') in response.data

def test_project_stats_view(client, auth, test_team):
    """Test widoku statystyk projektu."""
    auth.login()
    
    response = client.get(f'/teams/{test_team.id}/projects/TEST-1/stats')
    assert response.status_code == 200
    assert b'Statystyki Projektu' in response.data
    assert b'TEST-1' in response.data 