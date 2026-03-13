import os
from celery import Celery

# Default to local redis if not configured
redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=redis_url,
    backend=result_backend,
    include=[
        "app.usecases.communicators",
        "app.usecases.front_office_tasks",
    ],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Hong_Kong',
    enable_utc=False,
    task_track_started=True,
    result_expires=86400,
    result_backend_transport_options={
        'retry_policy': {
            'max_retries': 3,
            'interval_start': 0.2,
            'interval_step': 0.5,
            'interval_max': 3,
        },
    },
)
