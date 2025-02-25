import pytest
from app.services.portfolio_service import (
    create_portfolio, get_portfolio, update_portfolio,
    add_project_to_portfolio, remove_project_from_portfolio
)

def test_create_portfolio(client, auth):
    auth.login()
    
    # Test tworzenia portfolio
    response = client.post('/portfolio/create', data={
        'name': 'Test Portfolio',
        'description': 'Test Description',
        'client_name': 'Test Client'
    })
    assert response.status_code == 302
    
    # Test walidacji
    response = client.post('/portfolio/create', data={
        'name': '',
        'description': 'Test Description',
        'client_name': 'Test Client'
    })
    assert response.status_code == 400

def test_portfolio_permissions(client, auth):
    # Test dostępu bez logowania
    response = client.get('/portfolio/')
    assert response.status_code == 302
    
    # Test dostępu z niewłaściwą rolą
    auth.login('user')
    response = client.get('/portfolio/')
    assert response.status_code == 403
    
    # Test dostępu z właściwą rolą
    auth.login('admin')
    response = client.get('/portfolio/')
    assert response.status_code == 200 