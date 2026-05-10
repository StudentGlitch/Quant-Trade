import os
from celery import Celery

# Initialize Celery app
# Defaults to SQLite for local development to avoid Redis dependency
BROKER_URL = os.getenv("CELERY_BROKER_URL", "sqla+sqlite:///storage/db/celery_broker.db")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "db+sqlite:///storage/db/celery_results.db")

app = Celery('quant_swarm', broker=BROKER_URL, backend=RESULT_BACKEND)


# Phase 28: Global Configuration
app.conf.update(
    task_routes={
        'src.workers.background_tasks.execute_trades': {'queue': 'high_priority'},
        'src.workers.background_tasks.train_models': {'queue': 'ml_training'},
        'src.workers.background_tasks.scrape_osint': {'queue': 'scraping'},
        'src.workers.background_tasks.medic_healing_sweep': {'queue': 'scraping'},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone='Asia/Jakarta', # Standardized to Jakarta
    imports=['src.workers.background_tasks', 'src.workers.beat_schedule', 'src.workers.hydration_tasks', 'src.workflows.nightly_ml_cycle']
)

# Note: The actual beat_schedule is now defined in src/workers/beat_schedule.py 
# to keep the chrono-orchestration logic isolated.
