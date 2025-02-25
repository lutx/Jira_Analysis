import pytest
from app import create_app
from app.database import get_db, init_db

@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'DATABASE': ':memory:'
    })
    
    with app.app_context():
        init_db()
        
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_login(client):
    response = client.post('/auth/login', json={
        'user_name': 'test_user',
        'password': 'test_password'
    })
    assert response.status_code == 200 