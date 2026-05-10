from celery.schedules import crontab
from loguru import logger
from .celery_app import app

# Phase 28.2: Timezone-Aware Celery Beat CRON Definitions.
# Pinned to 'Asia/Jakarta' (WIB) for Indonesian market alignment.

app.conf.timezone = 'Asia/Jakarta'

# We define orchestrator tasks that trigger the DAGs
@app.task
def trigger_daily_idx_pipeline():
    from ..workflows.daily_trading_cycle import trigger_daily_trading_cycle
    # Fetch universe from DB or Config
    universe = ['BBCA.JK', 'TLKM.JK', 'ASII.JK'] 
    trigger_daily_trading_cycle(universe)

@app.task
def trigger_nightly_ml_check():
    from ..workflows.nightly_ml_cycle import trigger_nightly_ml_cycle
    trigger_nightly_ml_cycle()

@app.task
def trigger_weekend_maintenance_job():
    from ..workflows.weekend_maintenance import trigger_weekend_maintenance
    trigger_weekend_maintenance([])

app.conf.beat_schedule = {
    # 1. Daily Trading Cycle (Mon-Fri 16:15 WIB - Post-IDX Close)
    'daily-idx-trading-cycle': {
        'task': 'src.workers.beat_schedule.trigger_daily_idx_pipeline',
        'schedule': crontab(day_of_week='1-5', hour=16, minute=15),
    },
    
    # 2. Nightly ML Health Check (Mon-Fri 23:00 WIB)
    'nightly-ml-regime-check': {
        'task': 'src.workers.beat_schedule.trigger_nightly_ml_check',
        'schedule': crontab(day_of_week='1-5', hour=23, minute=0),
    },
    
    # 3. Weekend Maintenance (Saturday 02:00 WIB)
    'weekend-evolution-cycle': {
        'task': 'src.workers.beat_schedule.trigger_weekend_maintenance_job',
        'schedule': crontab(day_of_week='6', hour=2, minute=0),
    },
    
    # Low-priority medic sweep (Daily 04:00 WIB)
    'medic-self-healing': {
        'task': 'src.workers.background_tasks.medic_healing_sweep',
        'schedule': crontab(hour=4, minute=0),
    }
}

logger.info("Celery Beat Schedule synchronized with Asia/Jakarta timezone.")
