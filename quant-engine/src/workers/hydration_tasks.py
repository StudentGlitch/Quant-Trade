from .celery_app import app
from .background_tasks import QuantTask
from ..data.historical_hydrator import HistoricalHydrator
from loguru import logger
import os

@app.task(bind=True, base=QuantTask, queue='scraping')
def hydrate_ticker_task(self, ticker: str):
    """Distributed task for historical backfill."""
    logger.info(f"Celery Task: Hydrating {ticker}")
    
    workspace_root = os.getenv("WORKSPACE_ROOT", os.getcwd())
    hydrator = HistoricalHydrator(workspace_root)
    
    success = hydrator.hydrate_ticker(ticker)
    
    if not success:
        # Conceptually log failure to a 'Problematic Tickers' table
        pass
        
    return {"ticker": ticker, "success": success}

def dispatch_hydration_swarm(repo):
    """Orchestrator to trigger the 900+ ticker backfill."""
    logger.info("Dispatching Hydration Swarm...")
    
    tickers_df = repo.con.execute("SELECT ticker FROM idx_metadata").df()
    tickers = tickers_df['ticker'].tolist()
    
    for ticker in tickers:
        hydrate_ticker_task.delay(ticker)
        
    logger.success(f"Dispatched {len(tickers)} hydration tasks to Celery.")
