from app.forms import UserSettingsForm
from app.forms.admin import JiraSettingsForm
from wtforms.validators import URL

def test_user_settings_form():
    """Test user settings form."""
    form = UserSettingsForm()
    assert form.display_name is not None
    assert form.email is not None

    # Test valid data
    form = UserSettingsForm(data={
        'display_name': 'Test User',
        'email': 'test@example.com',
        'submit': True
    })
    assert form.validate() is True

    # Test invalid email
    form = UserSettingsForm(data={
        'display_name': 'Test User',
        'email': 'invalid-email',
        'submit': True
    })
    assert form.validate() is False

def test_jira_settings_form():
    """Test JIRA settings form."""
    form = JiraSettingsForm()
    assert form.jira_url is not None
    assert form.jira_username is not None
    assert form.jira_token is not None

    # Test valid data
    form = JiraSettingsForm(data={
        'jira_url': 'https://jira-test.lbpro.pl',
        'jira_username': 'test',
        'jira_token': 'token123',
        'is_active': True,
        'submit': True
    })
    assert form.validate() is True

    # Test invalid URL
    form = JiraSettingsForm(data={
        'jira_url': 'invalid-url',
        'jira_username': 'test',
        'jira_token': 'token123',
        'submit': True
    })
    assert form.validate() is False 