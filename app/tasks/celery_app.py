from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "furu_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.email", "app.tasks.ai_processing", "app.tasks.backtest"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)