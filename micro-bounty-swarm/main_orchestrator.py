import asyncio
import logging
import time
from pathlib import Path
import sys

# Setup paths and imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.db_manager import init_db
from agents.discovery_agent import run_discovery
from agents.solver_agent import run_solver
from agents.verifier_agent import run_verifier
from agents.submission_agent import run_submission
from agents.learning_loop import summarize_iteration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - ORCHESTRATOR - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).resolve().parent / "logs" / "system_execution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("orchestrator")

async def main_loop():
    """Continuous orchestration loop managing the swarm topology."""
    logger.info("Initializing Micro-Bounty Autonomous Swarm...")
    init_db()
    
    iteration = 1
    while True:
        logger.info(f"--- Starting Swarm Iteration {iteration} ---")
        try:
            # 1. Discovery Phase (Async to utilize Obscura/Playwright)
            await run_discovery()
            
            # 2. Solving Phase (Sync via subprocess to Hermes CLI)
            await asyncio.to_thread(run_solver)
            
            # 3. Verification Phase
            await asyncio.to_thread(run_verifier)
            
            # 4. Submission Phase (Async Playwright)
            await run_submission()
            
            # 5. Learning Loop Phase
            await asyncio.to_thread(summarize_iteration, iteration)
            
        except Exception as e:
            logger.error(f"Critical error in main loop during iteration {iteration}: {e}")
            # Exhaustive try/except ensures the daemon never crashes entirely
            
        logger.info(f"--- Completed Swarm Iteration {iteration}. Sleeping for 60s... ---")
        await asyncio.sleep(60) # Prevent aggressive rate limiting
        iteration += 1

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Swarm daemon terminated gracefully by user.")
