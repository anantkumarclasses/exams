# backend/app/celery_app.py

from celery import Celery
import os

def make_celery(app=None):
    broker_url = os.getenv("CELERY_BROKER_URL")
    result_backend = os.getenv("CELERY_RESULT_BACKEND")

    return Celery(
        app.import_name if app else __name__,
        broker=broker_url,
        backend=result_backend,
        include=[
            'app.tasks.reminders',
            'app.tasks.monthly_reports',
            'app.tasks.csv_export',
        ]
    )

celery = make_celery()
