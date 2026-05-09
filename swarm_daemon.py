
import asyncio
import time
import subprocess
import sys
from pathlib import Path
from loguru import logger
import os

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
ORCHESTRATOR_PATH = BASE_DIR / "orchestrator.py"

# Add utils to path for zombie sweeper
sys.path.insert(0, str(BASE_DIR))
from src.utils.process_utils import kill_zombie_locks

logging_config = {
    "handlers": [
        {"sink": sys.stdout, "format": "{time} - {level} - {message}"},

        {"sink": BASE_DIR / "logs" / "swarm_daemon.log", "rotation": "10 MB"}
    ]
}
logger.configure(**logging_config)

async def run_swarm_continuously():
    """
    Autonomous Daemon Loop for the Darwinian Quant Swarm.
    Configured for 6-hour Intensive Training Phase.
    """
    logger.info("Starting Darwinian Quant Swarm Daemon [INTENSIVE TRAINING MODE]...")
    
    # Pre-flight Zombie Sweep (PRD Bug Fix)
    kill_zombie_locks()
    
    iteration = 1
    # Run for 12 iterations (6 hours at 30 min intervals)
    max_intensive_iterations = 12
    
    while True:
        logger.info(f"--- Starting Swarm Cycle {iteration} ---")
        
        # Ensure clean state for every cycle
        kill_zombie_locks()
        
        try:
            # PRD 7.5.1: State Ingestion and full pipeline
            # Use sys.executable to ensure we use the same python environment
            process = subprocess.Popen(
                [sys.executable, str(ORCHESTRATOR_PATH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                cwd=str(BASE_DIR) # Explicitly set CWD to quant-engine
            )
            
            # Stream merged output to daemon log and monitor for IOErrors
            io_lock_error = False
            for line in process.stdout:
                line_str = line.strip()
                logger.info(f"[Orchestrator] {line_str}")
                if "IOException" in line_str or "process cannot access the file" in line_str:
                    io_lock_error = True
            
            process.wait()
            
            if process.returncode == 0:
                logger.success(f"Swarm Cycle {iteration} completed successfully.")
            elif io_lock_error:
                logger.error(f"Swarm Cycle {iteration} blocked by file lock. Retrying in 5s...")
                kill_zombie_locks()
                await asyncio.sleep(5)
                continue # Retry same iteration
            else:
                logger.error(f"Swarm Cycle {iteration} failed with exit code {process.returncode}.")
                
        except Exception as e:
            logger.critical(f"Critical error in daemon loop: {e}")

        if iteration <= max_intensive_iterations:
            logger.info(f"Intensive Training: Cycle {iteration}/{max_intensive_iterations} complete. Sleeping for 30 minutes...")
            await asyncio.sleep(1800)
        else:
            logger.info("Intensive Training Phase complete. Reverting to standard 1-hour cycle.")
            logger.info("Swarm Cycle complete. Sleeping for 1 hour...")
            await asyncio.sleep(3600)
            
        iteration += 1

if __name__ == "__main__":
    try:
        asyncio.run(run_swarm_continuously())
    except KeyboardInterrupt:
        logger.info("Daemon terminated by user.")
