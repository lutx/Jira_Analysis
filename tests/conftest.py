import pytest
from app import create_app
from app.extensions import db
from app.models import User, Role, Team, Project

@pytest.fixture
def app():
    """Create application for the tests."""
    app = create_app('tests.config.TestConfig')
    
    with app.app_context():
        db.create_all()
        _setup_test_data()
        yield app
        db.session.remove()
        db.drop_all()

def _setup_test_data():
    """Create test data."""
    # Create roles
    admin_role = Role(name='admin', description='Administrator')
    user_role = Role(name='user', description='Regular user')
    db.session.add_all([admin_role, user_role])
    
    # Create test user
    user = User(
        username='test',
        email='test@example.com',
        is_active=True
    )
    user.set_password('test123')
    user.roles.append(user_role)
    db.session.add(user)
    
    # Create test admin
    admin = User(
        username='admin',
        email='admin@example.com',
        is_active=True,
        is_superadmin=True
    )
    admin.set_password('admin123')
    admin.roles.append(admin_role)
    db.session.add(admin)
    
    db.session.commit() 