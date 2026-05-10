from .celery_app import app
from .background_tasks import QuantTask
from loguru import logger
import os
from ..data.duckdb_repo import DuckDBRepo

@app.task(bind=True, base=QuantTask)
def run_autonomous_dev_cycle(self):
    """Phase 30.1: Trigger Auto-Dev Agent."""
    logger.info("Starting Autonomous Quant Developer cycle...")
    from ..execution.autonomous_dev_agent import AutonomousDevAgent
    
    workspace_root = os.getenv("WORKSPACE_ROOT", os.getcwd())
    repo = DuckDBRepo(os.path.join(workspace_root, "storage", "db", "quant_data.duckdb"))
    agent = AutonomousDevAgent(repo, workspace_root)
    
    # Mocking the hypothesis generation process
    features_to_evolve = [("dynamic_vol_skew", "Analyze implied volatility smile asymmetries")]
    
    for feat, prompt in features_to_evolve:
        agent.evolve_feature(feat, prompt)
        
    return "auto_dev_cycle_complete"

@app.task(bind=True, base=QuantTask)
def generate_pitch_books(self):
    """Phase 30.2: Trigger Pitch Book Generation."""
    logger.info("Starting automated Pitch Book generation...")
    from ..execution.pitch_generator import PitchBookGenerator
    
    workspace_root = os.getenv("WORKSPACE_ROOT", os.getcwd())
    repo = DuckDBRepo(os.path.join(workspace_root, "storage", "db", "quant_data.duckdb"))
    generator = PitchBookGenerator(repo, workspace_root)
    
    generator.generate_monthly_pitchbook()
    return "pitch_book_generated"
