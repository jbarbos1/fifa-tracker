from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.daily_report import generate_daily_report
from app.jobs.db_maintenance import check_database_health
from app.jobs.usage_tracking import track_usage_snapshot

scheduler = BackgroundScheduler()


def run_with_app_context(app, job_func):
    with app.app_context():
        job_func


def start_jobs(app):
    scheduler.add_job(
        func=lambda: run_with_app_context(app, check_database_health),
        trigger='interval',
        minutes=30,
        id='db_health_check',
        replace_existing=True
    )

    scheduler.add_job(
        func=lambda: run_with_app_context(app, track_usage_snapshot),
        trigger='interval',  # Interval relative to when app is running/started
        hours=1,
        id='usage_snapshot',
        replace_existing=True
    )

    scheduler.add_job(
        func=lambda: run_with_app_context(app, generate_daily_report),
        trigger='cron',  # Trigger is based on actual time zone
        hour=8,
        minute=0,
        id='daily_status_report',
        replace_existing=True
    )

    scheduler.start()
