from kombu import Exchange, Queue

CELERY_ACCEPT_CONTENT=['json']
CELERY_TASK_SERIALIZER='json'
CELERY_RESULT_SERIALIZER='json'
CELERY_BROKER_URL='redis://localhost:6379/0'
CELERY_BACKEND='redis://localhost:6379/1'
CELERY_QUEUES = (
    Queue('transplant', Exchange('transplant'), routing_key='transplant'),
)