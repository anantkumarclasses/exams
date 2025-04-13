# backend/app/celery_app.py

from celery import Celery
import os
from dotenv import load_dotenv

# Load .env variables if needed
load_dotenv()

def make_celery(app_name='quiz_master'):
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    return Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=[
            'app.tasks.reminders',
            'app.tasks.monthly_reports',
            'app.tasks.csv_export',
        ]
    )

celery = make_celery()
