import asyncio
import aiohttp
import pandas as pd
import yfinance as yf
from loguru import logger
from typing import List
from pathlib import Path
from .job_queue import JobQueue

class AsyncYFinanceClient:
    """
    Asynchronous historical data fetcher for the job queue (PRD Phase 0.4).
    Uses a strict semaphore to prevent IP bans.
    """
    def __init__(self, queue: JobQueue, max_concurrent: int = 5):
        self.queue = queue
        # PRD 0.4.2: Strict concurrency limit
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.parquet_dir = self.base_dir / "storage" / "parquet_data"
        self.parquet_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_ticker(self, ticker: str):
        """Fetch 10 years of data and save to Hive-partitioned Parquet."""
        async with self.semaphore:
            logger.info(f"Fetching full history for {ticker}...")
            
            try:
                # We use yfinance in a thread to avoid blocking the async loop
                # Alternatively, we could use aiohttp directly to the Yahoo API, 
                # but yfinance handles the crumb/cookie logic well.
                df = await asyncio.to_thread(
                    yf.download, 
                    ticker, 
                    period="max", # PRD 0.4.2: Fetch 10 years/max data
                    auto_adjust=True, 
                    progress=False
                )
                
                if df.empty:
                    logger.warning(f"No data returned for {ticker}.")
                    self.queue.update_job_status(ticker, 'FAIL', error_log="Empty DataFrame")
                    return

                # Flatten multi-index if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                df.index.name = 'date'
                df = df.reset_index()
                
                # Standardize names for SQL/Parquet
                df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
                
                # Ensure adj_close exists
                if 'close' in df.columns and 'adj_close' not in df.columns:
                    df['adj_close'] = pd.to_numeric(df['close'], errors='coerce')
                    
                # PRD 0.4.3: Parquet Partitioning
                ticker_dir = self.parquet_dir / f"ticker={ticker}"
                ticker_dir.mkdir(exist_ok=True)
                filepath = ticker_dir / "data.parquet"
                
                # Save using pyarrow engine
                df.to_parquet(filepath, engine='pyarrow', index=False)
                
                logger.success(f"Saved Parquet for {ticker} ({len(df)} rows)")
                # PRD 0.4.4: State Commitment
                self.queue.update_job_status(ticker, 'SUCCESS')
                
            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")
                self.queue.update_job_status(ticker, 'FAIL', error_log=str(e))

    async def run_queue_consumer(self, batch_size: int = 5):
        """Consume the job queue continuously."""
        logger.info("Starting Async Queue Consumer...")
        
        while True:
            # PRD 0.4.1: Queue Consumption
            pending_tickers = self.queue.get_pending_jobs(limit=batch_size)
            
            if not pending_tickers:
                logger.info("No pending jobs in queue. Consumer sleeping.")
                break # Exit when queue is empty
                
            # Mark as PROCESSING
            for ticker in pending_tickers:
                self.queue.update_job_status(ticker, 'PROCESSING')
                
            # Fetch concurrently, bounded by semaphore
            tasks = [self.fetch_ticker(t) for t in pending_tickers]
            await asyncio.gather(*tasks)
            
            # Brief pause between batches
            await asyncio.sleep(2)
