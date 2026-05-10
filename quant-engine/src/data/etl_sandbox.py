import pandas as pd
import numpy as np
from loguru import logger
import importlib.util
from pathlib import Path
from playwright.async_api import async_playwright
import asyncio
from ..data.duckdb_repo import DuckDBRepo

class ETLSandbox:
    """
    Phase 8.2: The ETL Sandbox & Execution.
    Runs autonomous scrapers via Obscura CDP and normalizes time-series.
    """
    
    CDP_URL = "http://127.0.0.1:9222"

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.scraper_dir = Path(__file__).resolve().parent / "autonomous_scrapers"
        self._init_ledger()

    def _init_ledger(self):
        """Phase 6.1: Initialize OSINT tables."""
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS osint_datasets_ledger (
                dataset_id VARCHAR PRIMARY KEY,
                target_url TEXT,
                description TEXT,
                frequency VARCHAR,
                python_script_path TEXT,
                last_successful_run TIMESTAMP,
                consecutive_failures INT DEFAULT 0,
                status VARCHAR
            );
        """)
        
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS autonomous_timeseries_data (
                date DATE,
                dataset_id VARCHAR,
                value DOUBLE,
                PRIMARY KEY (date, dataset_id)
            );
        """)

    async def run_scrapers(self):
        """Orchestrate the execution of all active autonomous scrapers."""
        logger.info("ETL Sandbox: Starting autonomous OSINT acquisition cycle...")
        
        active_scrapers = self.repo.execute("SELECT * FROM osint_datasets_ledger WHERE status = 'ACTIVE'").df()
        
        if active_scrapers.empty:
            logger.info("No active autonomous scrapers found.")
            return

        async with async_playwright() as p:
            try:
                # Connect to Obscura CDP (PRD 8.2.2)
                browser = await p.chromium.connect_over_cdp(self.CDP_URL)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = await context.new_page()
                
                for _, row in active_scrapers.iterrows():
                    dataset_id = row['dataset_id']
                    script_path = row['python_script_path']
                    
                    try:
                        # 1. Dynamic Import
                        spec = importlib.util.spec_from_file_location(dataset_id, script_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 2. Execute Scraper
                        # Expecting: async def scrape_data(page) -> pd.Series
                        data_series = await module.scrape_data(page)
                        
                        if not data_series.empty:
                            # 3. Forward-Fill Normalization (Section 7.1)
                            self._process_and_store(dataset_id, data_series)
                            
                            # 4. Update Ledger
                            self.repo.execute("""
                                UPDATE osint_datasets_ledger 
                                SET last_successful_run = CURRENT_TIMESTAMP, consecutive_failures = 0
                                WHERE dataset_id = ?
                            """, [dataset_id])
                            logger.success(f"ETL: Successfully updated {dataset_id}")
                        else:
                            raise ValueError("Scraper returned empty series.")
                            
                    except Exception as e:
                        logger.error(f"ETL: Scraper '{dataset_id}' failed: {e}")
                        self._handle_failure(dataset_id)
                        
                await browser.close()
            except Exception as e:
                logger.error(f"ETL Sandbox: CDP Connection failed: {e}. Ensure Obscura (9222) is running.")

    def _process_and_store(self, dataset_id: str, series: pd.Series):
        """Apply frequency alignment and store in DuckDB."""
        # 1. Fetch official trading calendar
        calendar = self.repo.execute("SELECT DISTINCT date FROM feature_store ORDER BY date").df()['date'].tolist()
        if not calendar:
            logger.warning("No calendar found in feature_store. Using raw dates.")
            calendar = pd.date_range(series.index.min(), series.index.max(), freq='D').date
        else:
            calendar = [pd.to_datetime(d).date() for d in calendar]

        # 2. Section 7.1: Forward-Fill Alignment
        # We reindex to the full calendar and ffill
        df_full = pd.DataFrame(index=pd.DatetimeIndex(calendar))
        df_data = series.to_frame(name='value')
        df_data.index = pd.to_datetime(df_data.index)
        
        # Merge and Forward-Fill
        merged = df_full.join(df_data, how='left').ffill().dropna()
        
        # 3. Upsert into DuckDB
        records = []
        for date, row in merged.iterrows():
            records.append((date.date(), dataset_id, float(row['value'])))
            
        if records:
            self.repo.con.executemany("""
                INSERT OR REPLACE INTO autonomous_timeseries_data (date, dataset_id, value)
                VALUES (?, ?, ?)
            """, records)

    def _handle_failure(self, dataset_id: str):
        """Update failure count and mark as BROKEN if threshold met."""
        self.repo.execute("""
            UPDATE osint_datasets_ledger 
            SET consecutive_failures = consecutive_failures + 1
            WHERE dataset_id = ?
        """, [dataset_id])
        
        fail_count = self.repo.execute("SELECT consecutive_failures FROM osint_datasets_ledger WHERE dataset_id = ?", [dataset_id]).fetchone()[0]
        if fail_count > 3:
            self.repo.execute("UPDATE osint_datasets_ledger SET status = 'BROKEN' WHERE dataset_id = ?", [dataset_id])
            logger.critical(f"ETL: Scraper '{dataset_id}' marked as BROKEN after {fail_count} failures.")

    def register_dataset(self, dataset_id: str, url: str, description: str, script_path: str):
        """Manual registration of a new autonomous dataset."""
        self.repo.execute("""
            INSERT OR REPLACE INTO osint_datasets_ledger 
            (dataset_id, target_url, description, frequency, python_script_path, status)
            VALUES (?, ?, ?, 'DAILY', ?, 'ACTIVE')
        """, [dataset_id, url, description, script_path])
