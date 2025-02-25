from app import create_app
from app.extensions import celery

app = create_app()
app.app_context().push()  # This ensures we have application context

# Configure Celery
celery.conf.update(
    broker_url=app.config['CELERY_BROKER_URL'],
    result_backend=app.config['CELERY_RESULT_BACKEND'],
    timezone=app.config['CELERY_TIMEZONE'],
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    include=['app.tasks.jira_sync']
)

if __name__ == '__main__':
    celery.start() 