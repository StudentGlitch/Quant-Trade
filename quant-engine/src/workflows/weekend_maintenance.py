from celery import chain
from loguru import logger
from ..workers.background_tasks import (
    rebuild_parquet_hive,
    build_dpo_dataset,
    train_qlora_adapter,
    hot_swap_vllm
)
from ..workers.hydration_tasks import hydrate_ticker_task

def trigger_weekend_maintenance(universe: list):
    """
    Phase 28.1: The Weekend Maintenance DAG.
    Scheduled for Saturday off-peak.
    Hydration -> Parquet Hive Rebuild -> DPO Builder -> QLoRA Train -> vLLM Swap.
    """
    logger.info("Initiating Weekend Maintenance & Proprietary Tuning...")
    
    workflow = chain(
        # 1. Rebuild and Optimize the Parquet Data Lake
        rebuild_parquet_hive.s(),
        
        # 2. LLM Proprietary Evolution (Phase 27)
        build_dpo_dataset.s(),
        train_qlora_adapter.s(),
        hot_swap_vllm.s()
    )
    
    return workflow.apply_async()
