"""Celery configuration and app instance."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "aae_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        # Token expiry check - Daily at 2:00 AM UTC
        "check-token-expiry": {
            "task": "app.tasks.token_refresh.check_token_expiry",
            "schedule": crontab(hour=2, minute=0),
        },
        # Data fetch - Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
        "fetch-ad-data": {
            "task": "app.tasks.data_fetch.fetch_ad_data",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        # Daily report generation - Daily at 9:00 AM UTC
        "generate-daily-report": {
            "task": "app.tasks.reports.generate_daily_report",
            "schedule": crontab(hour=9, minute=0),
        },
        # Anomaly detection - Every hour
        "detect-anomalies": {
            "task": "app.tasks.anomaly_detection.detect_anomalies",
            "schedule": crontab(minute=0),
        },
        # Campaign rule checking - Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
        "check-campaign-rules": {
            "task": "app.tasks.rule_check.check_campaign_rules",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    },
)

# Auto-discover tasks from app.tasks module
celery_app.autodiscover_tasks(["app.tasks"])
