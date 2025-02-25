def test_export_efficiency_csv(client, team):
    """Test eksportu raportu efektywności do CSV."""
    response = client.get(f'/api/teams/{team.id}/export/efficiency?format=csv')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv' 