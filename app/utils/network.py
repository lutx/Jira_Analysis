import functools
import requests
from flask import current_app
from requests.exceptions import RequestException

def handle_network_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RequestException as e:
            current_app.logger.error(f"Network error in {func.__name__}: {str(e)}")
            raise
        except Exception as e:
            current_app.logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise
    return wrapper 