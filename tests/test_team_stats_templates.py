def test_template_error_handling(app, client, auth, test_team):
    """Test obsługi błędów w szablonach."""
    auth.login()
    
    # Test braku danych
    with app.test_client() as c:
        with app.app_context():
            response = c.get(f'/teams/{test_team.id}/members/nonexistent/stats')
            assert response.status_code == 404
            assert b'Nie znaleziono użytkownika' in response.data
    
    # Test błędów renderowania
    with app.test_client() as c:
        with app.app_context():
            # Symuluj błąd podczas renderowania
            def mock_render(*args, **kwargs):
                raise ValueError("Test error")
            
            app.jinja_env.get_template = mock_render
            
            response = c.get(f'/teams/{test_team.id}/members/user1/stats')
            assert response.status_code == 500
            assert b'Wystąpił błąd podczas generowania widoku' in response.data

def test_template_data_sanitization(app, client, auth, test_team):
    """Test sanityzacji danych w szablonach."""
    auth.login()
    
    # Test XSS
    with app.test_client() as c:
        with app.app_context():
            response = c.get(f'/teams/{test_team.id}/members/<script>alert("xss")</script>/stats')
            assert response.status_code == 404
            assert b'<script>' not in response.data
    
    # Test SQL Injection
    with app.test_client() as c:
        with app.app_context():
            response = c.get(f'/teams/{test_team.id}/members/1 OR 1=1/stats')
            assert response.status_code == 404
            assert b'SQL error' not in response.data 