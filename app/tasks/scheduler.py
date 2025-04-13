# backend/app/tasks/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import threading
from .reminders import send_daily_reminders
from .monthly_reports import send_monthly_reports

scheduler_lock = threading.Lock()

def start_scheduler():
    with scheduler_lock:
        scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(10)})
        scheduler.add_job(send_daily_reminders, 'cron', hour=19, minute=0)
        scheduler.add_job(send_monthly_reports, 'cron', day=30, hour=22, minute=0)
        scheduler.start()