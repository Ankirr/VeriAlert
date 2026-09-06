"""
Celery Task Queue & Periodic Scheduler Configuration for VeriAlert.
Uses local Redis instance (redis://localhost:6379/0) as broker and result backend.
Schedules automated multi-agent pipeline runs every 15 minutes.
"""
import os
import logging
from celery import Celery
from celery.schedules import crontab
from app.config import settings

logger = logging.getLogger("VeriAlertCelery")

# Initialize Celery app
celery_app = Celery(
    "verialert_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,  # 15 minutes max execution timeout
    worker_concurrency=2,
    broker_connection_retry_on_startup=True
)

# Automated Periodic Schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    "periodic-disaster-intelligence-pipeline": {
        "task": "app.tasks.run_disaster_pipeline_task",
        "schedule": 900.0,  # Every 15 minutes
        "options": {"queue": "disaster_pipeline"}
    }
}
