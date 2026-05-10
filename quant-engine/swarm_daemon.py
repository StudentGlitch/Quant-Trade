import subprocess
import sys
import os
from pathlib import Path
from loguru import logger
import time

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def run_local_swarm():
    """
    Phase 22: High-Availability Local Entrypoint.
    Launches Celery Worker, Beat, and API in the background.
    """
    logger.info("Starting local Swarm infrastructure...")
    
    # Force SQLite for local background run to avoid Redis dependency
    os.environ["CELERY_BROKER_URL"] = "sqla+sqlite:///storage/db/celery_broker.db"
    os.environ["CELERY_RESULT_BACKEND"] = "db+sqlite:///storage/db/celery_results.db"



    # 1. Start Redis (Assuming installed locally, or we'd use docker-compose)
    # logger.info("Starting Redis...")
    # subprocess.Popen(["redis-server"], shell=True)
    # time.sleep(2)

    # 2. Start Celery Worker
    logger.info("Launching Celery Worker [High Priority & ML]...")
    subprocess.Popen([
        sys.executable, "-m", "celery", "-A", "src.workers.celery_app", "worker", 
        "--loglevel=info", "-P", "solo" # 'solo' is safer for some Windows environments
    ], cwd=str(BASE_DIR))

    # 3. Start Celery Beat (Scheduler)
    logger.info("Launching Celery Beat [Scheduler]...")
    subprocess.Popen([
        sys.executable, "-m", "celery", "-A", "src.workers.celery_app", "beat", 
        "--loglevel=info"
    ], cwd=str(BASE_DIR))

    # 4. Start FastAPI Backend (Optional entrypoint)
    logger.info("Launching Quant API...")
    subprocess.Popen([
        sys.executable, "-m", "uvicorn", "src.api.endpoints.system_health:app", 
        "--host", "0.0.0.0", "--port", "8000"
    ], cwd=str(BASE_DIR))

    logger.success("Darwinian Quant Swarm is now running in the background.")
    logger.info("Check celery_worker.log and celery_beat.log for details.")

if __name__ == "__main__":
    run_local_swarm()
    # Keep main process alive to monitor children if desired, or exit
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        logger.info("Shutting down local swarm launcher.")
