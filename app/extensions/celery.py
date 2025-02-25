from celery import Celery
from flask import Flask

def init_celery(app: Flask = None) -> Celery:
    """Initialize Celery instance."""
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND'],
        include=['app.tasks.jira_sync']
    )
    
    # Update celery config from Flask config
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery 