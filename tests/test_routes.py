def test_routes(client):
    """Test if all routes are accessible."""
    routes = [
        ('/', 302),  # Redirects to login
        ('/auth/login', 200),
        ('/dashboard', 302),  # Requires auth
        ('/worklog', 302),  # Requires auth
        ('/admin', 302),  # Requires admin
    ]
    
    for route, expected_status in routes:
        response = client.get(route)
        assert response.status_code == expected_status 