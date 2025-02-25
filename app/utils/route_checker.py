from flask import current_app, url_for, request
from werkzeug.routing import BuildError
import logging
import os
from werkzeug.test import EnvironBuilder
from flask import _request_ctx_stack

logger = logging.getLogger(__name__)

def create_test_request_context():
    """Create a test request context for URL generation."""
    builder = EnvironBuilder(base_url='http://localhost:5003')
    env = builder.get_environ()
    return current_app.test_request_context(env)

def verify_endpoint(endpoint):
    """Verify a single endpoint."""
    try:
        with create_test_request_context():
            url = url_for(endpoint)
            if not isinstance(url, str):
                raise ValueError(f"Generated URL is not a string: {type(url)}")
            return None
    except Exception as e:
        error = {
            'endpoint': endpoint,
            'error': str(e),
            'error_type': type(e).__name__
        }
        logger.error(f"Route error for endpoint {endpoint}: {str(e)}")
        return error

def verify_all_routes():
    """Verify all routes in the application."""
    routes_to_check = []
    errors = []
    
    try:
        # Zbierz wszystkie endpointy
        for rule in current_app.url_map.iter_rules():
            if 'GET' in rule.methods and not rule.arguments:
                routes_to_check.append(rule.endpoint)

        # Sprawdź każdy endpoint
        with create_test_request_context():
            for endpoint in routes_to_check:
                try:
                    error = verify_endpoint(endpoint)
                    if error:
                        errors.append(error)
                except Exception as e:
                    logger.error(f"Error verifying endpoint {endpoint}: {str(e)}")
                    errors.append({
                        'endpoint': endpoint,
                        'error': str(e)
                    })
                    
    except Exception as e:
        logger.error(f"Error in route verification: {str(e)}")
        
    return errors

def get_template_endpoints(template_path):
    """Extract all url_for endpoints from a template."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not isinstance(content, str):
                logger.error(f"File content is not a string: {type(content)}")
                return set()
        
        # Ulepszone wyrażenie regularne do znajdowania url_for
        import re
        pattern = r"url_for\(['\"]([^'\"]+)['\"](?:\s*,\s*[^)]+)?\)"
        matches = re.findall(pattern, content)
        return set(matches) if matches else set()
        
    except Exception as e:
        logger.error(f"Error reading template {template_path}: {str(e)}")
        return set()

def verify_routing(app):
    """Verify all routes in the application."""
    errors = []
    try:
        for rule in app.url_map.iter_rules():
            try:
                # Test if route can be accessed
                app.test_client().get(rule.rule)
            except Exception as e:
                errors.append({
                    'endpoint': rule.endpoint,
                    'rule': rule.rule,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
    except Exception as e:
        app.logger.error(f"Error in route verification: {str(e)}")
    return errors

def verify_template_routes(app):
    """Verify all template routes."""
    missing_templates = []
    try:
        for rule in app.url_map.iter_rules():
            if 'GET' in rule.methods:
                view_func = app.view_functions[rule.endpoint]
                # Check if view function returns a template
                if hasattr(view_func, '_template'):
                    template_name = view_func._template
                    if not app.jinja_env.get_template(template_name):
                        missing_templates.append(template_name)
    except Exception as e:
        app.logger.error(f"Error verifying template routes: {str(e)}")
    return missing_templates

def print_route_verification_results(errors):
    """Print route verification results in a readable format."""
    if not errors:
        print("\nAll routes are valid! ✅")
        return
    
    print("\nRouting Errors Found:")
    print("-" * 80)
    
    # Grupuj błędy według typu
    template_errors = [e for e in errors if 'template' in e]
    route_errors = [e for e in errors if 'template' not in e]
    
    if route_errors:
        print("\nRoute Errors:")
        for error in route_errors:
            print(f"Endpoint: {error['endpoint']}")
            print(f"Error: {error['error']}")
            print(f"Type: {type(error['error']).__name__}")
            print("-" * 40)
    
    if template_errors:
        print("\nTemplate Errors:")
        for error in template_errors:
            print(f"Template: {error['template']}")
            print(f"Endpoint: {error.get('endpoint', 'N/A')}")
            print(f"Error: {error['error']}")
            print(f"Type: {type(error['error']).__name__}")
            print("-" * 40) 