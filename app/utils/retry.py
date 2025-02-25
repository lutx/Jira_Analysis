import functools
from time import sleep
from flask import current_app

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        current_app.logger.error(f"Max retries ({max_retries}) reached for {func.__name__}: {str(e)}")
                        raise
                    current_app.logger.warning(f"Retry {retries}/{max_retries} for {func.__name__}: {str(e)}")
                    sleep(delay * retries)  # Zwiększający się delay
            return None
        return wrapper
    return decorator 