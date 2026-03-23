from celery import Celery
from celery.schedules import crontab
from core.config import settings

celery_app = Celery(
    "tac_pmc_crm",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["apps.api.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "refresh-materialized-reports": {
            "task": "tasks.refresh_all_reports",
            "schedule": 3600.0, # Every hour
        },
        "generate-daily-ai-summaries": {
            "task": "tasks.generate_daily_ai_summaries",
            "schedule": crontab(hour=0, minute=0),  # Midnight UTC daily
        },
    }
)

if __name__ == "__main__":
    celery_app.start()
