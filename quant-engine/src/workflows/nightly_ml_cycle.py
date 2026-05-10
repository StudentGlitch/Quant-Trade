from celery import chain
from loguru import logger
from ..workers.background_tasks import (
    calculate_psi_drift,
    train_qlora_adapter,
    sync_global_models
)
from ..workers.celery_app import app

@app.task
def nightly_ml_router(drift_detected: bool):
    """Router task to trigger retraining only if drift exceeds threshold."""
    if drift_detected:
        logger.warning("Significant feature drift detected (> 0.2 PSI). Triggering retraining.")
        workflow = chain(train_qlora_adapter.s(), sync_global_models.s())
        return workflow.apply_async()
    else:
        logger.info("Models remain statistically stable. Skipping nightly retraining.")
        return "Models Healthy"

def trigger_nightly_ml_cycle():
    """
    Phase 28.1: The Nightly ML DAG.
    Calculate Drift -> (Conditional) Retrain -> Sync.
    """
    logger.info("Initiating Nightly ML Drift Analysis...")
    
    workflow = chain(
        calculate_psi_drift.s(),
        nightly_ml_router.s()
    )
    
    return workflow.apply_async()
