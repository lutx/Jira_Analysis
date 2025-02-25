from flask_login import login_user
from app.utils.template_helpers import get_menu_items

def test_menu_items_for_anonymous_user(app):
    """Test menu items for anonymous user."""
    with app.test_request_context():
        menu_items = get_menu_items()
        assert len(menu_items) == 0  # Brak elementów menu dla niezalogowanego użytkownika

def test_menu_items_for_regular_user(app, test_user):
    """Test menu items for regular user."""
    with app.test_request_context():
        login_user(test_user)
        menu_items = get_menu_items()
        assert len(menu_items) == 2  # Dashboard i Worklog
        assert menu_items[0]['name'] == 'Dashboard'
        assert menu_items[1]['name'] == 'Worklog'

def test_menu_items_for_admin(app, admin_user):
    """Test menu items for admin user."""
    with app.test_request_context():
        login_user(admin_user)
        menu_items = get_menu_items()
        assert len(menu_items) == 4  # Dashboard, Worklog, Użytkownicy, Role
        assert any(item['name'] == 'Użytkownicy' for item in menu_items)
        assert any(item['name'] == 'Role' for item in menu_items) 