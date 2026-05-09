import asyncio
import sqlite3
import yfinance as yf
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger
from .duckdb_repo import DuckDBRepo

class AsyncYFinanceClient:
    """
    Asynchronous data ingestion using asyncio.to_thread and SQLite checkpoint/resume.
    Saves daily OHLCV directly to partitioned Parquet files managed by DuckDB.
    """
    def __init__(self, repo: DuckDBRepo, job_queue_path: str = "storage/db/job_queue.sqlite", parquet_dir: str = "storage/parquet_data"):
        self.repo = repo
        self.job_queue_path = job_queue_path
        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore = asyncio.Semaphore(5)

    def _get_pending_jobs(self) -> list[str]:
        conn = sqlite3.connect(self.job_queue_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM fetch_jobs WHERE status = 'PENDING'")
        jobs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jobs

    def _update_job_status(self, ticker: str, status: str, error_log: str = ""):
        conn = sqlite3.connect(self.job_queue_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            UPDATE fetch_jobs
            SET status = ?, last_attempt = ?, error_log = ?
            WHERE ticker = ?
        ''', (status, now, error_log, ticker))
        conn.commit()
        conn.close()

    def _fetch_sync(self, ticker: str, start_date: str) -> pd.DataFrame:
        """Synchronous fetch to be wrapped in a thread."""
        df = yf.download(ticker, start=start_date, auto_adjust=True, progress=False)
        return df

    async def _fetch_and_store_single(self, ticker: str, start_date: str):
        async with self.semaphore:
            logger.info(f"Fetching data for {ticker}...")
            try:
                # Run the blocking yf.download in a separate thread
                df = await asyncio.to_thread(self._fetch_sync, ticker, start_date)

                if df.empty:
                    logger.warning(f"No data returned for {ticker}")
                    self._update_job_status(ticker, 'FAILED', "No data returned")
                    return

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df.index.name = 'date'
                df = df.reset_index()
                df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
                df = df.loc[:, ~df.columns.duplicated()]
                df['ticker'] = str(ticker)

                # Format dates properly
                df['date'] = pd.to_datetime(df['date'])

                if 'close' in df.columns and 'adj_close' not in df.columns:
                    df['adj_close'] = pd.to_numeric(df['close'], errors='coerce')
                elif 'adj_close' in df.columns:
                    df['adj_close'] = pd.to_numeric(df['adj_close'], errors='coerce')

                # Extract year for partitioning
                df['year'] = df['date'].dt.year

                # Partitioning via pandas and DuckDB
                years = df['year'].unique()
                for year in years:
                    year_df = df[df['year'] == year].copy()
                    year_df['date'] = year_df['date'].dt.date # Convert to date for storage
                    year_df.drop(columns=['year'], inplace=True)

                    # Create partitioned directory structure: ticker=BBCA/year=2024.parquet
                    part_dir = self.parquet_dir / f"ticker={ticker}"
                    part_dir.mkdir(parents=True, exist_ok=True)
                    parquet_file = part_dir / f"year={year}.parquet"

                    # Instead of pyarrow write directly, we can use DuckDB to write the parquet
                    # which is highly performant and handles types well
                    self.repo.con.execute(f"COPY (SELECT * FROM year_df) TO '{parquet_file}' (FORMAT PARQUET)")

                self._update_job_status(ticker, 'SUCCESS')
                logger.success(f"Successfully stored Parquet data for {ticker}")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to fetch {ticker}: {error_msg}")
                self._update_job_status(ticker, 'FAILED', error_msg)

    async def run_ingestion(self, start_date: str):
        """Main entry point for async ingestion."""
        jobs = self._get_pending_jobs()
        if not jobs:
            logger.info("No PENDING jobs found in queue. Skipping ingestion.")
            return

        logger.info(f"Found {len(jobs)} pending jobs. Starting async ingestion...")
        tasks = [self._fetch_and_store_single(ticker, start_date) for ticker in jobs]
        await asyncio.gather(*tasks)
        logger.info("Async ingestion cycle completed.")

    def load_parquets_to_duckdb(self):
        """Loads or creates a view of the parquet files in DuckDB for analytical querying."""
        # Using DuckDB's powerful parquet wildcard reading
        parquet_glob = str(self.parquet_dir / "**" / "*.parquet")
        self.repo.con.execute("DROP VIEW IF EXISTS ohlcv_daily_parquet")
        # If no parquet files exist yet, this view creation might fail, so we wrap it
        try:
            self.repo.con.execute(f"CREATE VIEW ohlcv_daily_parquet AS SELECT * FROM read_parquet('{parquet_glob}', hive_partitioning=1)")
            logger.info("Parquet view ohlcv_daily_parquet created in DuckDB.")
        except Exception as e:
            logger.warning(f"Could not create parquet view (might be empty dir): {e}")
