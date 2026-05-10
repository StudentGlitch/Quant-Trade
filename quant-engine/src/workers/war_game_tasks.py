from .celery_app import app
from .background_tasks import QuantTask
from loguru import logger
import os
from ..data.duckdb_repo import DuckDBRepo

@app.task(bind=True, base=QuantTask, queue='ml_training')
def run_adversarial_war_game(self):
    """Phase 31: Trigger Nightly War Game Simulation."""
    logger.info("Starting Nightly Adversarial War Game...")
    from ..execution.adversarial_arena import AdversarialArena
    
    workspace_root = os.getenv("WORKSPACE_ROOT", os.getcwd())
    repo = DuckDBRepo(os.path.join(workspace_root, "storage", "db", "quant_data.duckdb"))
    
    arena = AdversarialArena(repo, workspace_root)
    arena.run_war_game()
    
    return "war_game_complete"
