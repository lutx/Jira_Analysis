import pytest
from flask import render_template_string
from app.templates.components.loading import loading_spinner
from app.templates.components.error_message import error_message

def test_loading_spinner(app):
    with app.test_request_context():
        template = """
            {% from 'components/loading.html' import loading_spinner %}
            {{ loading_spinner() }}
        """
        rendered = render_template_string(template)
        assert 'spinner-border' in rendered
        assert 'Loading...' in rendered

def test_error_message(app):
    with app.test_request_context():
        template = """
            {% from 'components/error_message.html' import error_message %}
            {{ error_message('Test error') }}
        """
        rendered = render_template_string(template)
        assert 'alert-danger' in rendered
        assert 'Test error' in rendered 