import yfinance as yf
import pandas as pd
import os
from pathlib import Path
from loguru import logger
from .corporate_actions import CorporateActions
from ..features.data_cleanser import DataCleanser

class HistoricalHydrator:
    """
    Phase 23.1: Deep Historical Ingestion Engine.
    Fetches 15+ years of data and applies adjustments.
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.storage_dir = self.workspace_root / "storage" / "parquet_data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def hydrate_ticker(self, ticker: str) -> bool:
        """Full backfill for a single ticker."""
        logger.info(f"Hydrating historical data for {ticker} (15Y+)...")
        
        try:
            tk = yf.Ticker(ticker)
            # Fetch max period (PRD 8.1)
            hist = tk.history(period="max", auto_adjust=False) # We want RAW for manual adjustment
            
            if hist.empty:
                logger.warning(f"No history found for {ticker}")
                return False

            # Reset index and standardize columns
            df = hist.reset_index()
            df.columns = [str(c).lower() for c in df.columns]
            
            # 1. Split & Dividend Adjustment
            splits = tk.splits
            dividends = tk.dividends
            
            df = CorporateActions.adjust_splits(df, splits)
            df = CorporateActions.calculate_dividend_yield(df, dividends)
            
            # 2. Data Cleansing
            df = DataCleanser.detect_limit_locks(df)
            df = DataCleanser.impute_missing_data(df)
            
            # 3. Store to Parquet (S3 Data Lake mock)
            ticker_dir = self.storage_dir / f"ticker={ticker}"
            ticker_dir.mkdir(parents=True, exist_ok=True)
            output_path = ticker_dir / "data.parquet"
            
            df['ticker'] = ticker
            df.to_parquet(output_path, index=False)
            
            logger.success(f"Hydration complete for {ticker}: {len(df)} rows.")
            return True

        except Exception as e:
            logger.error(f"Failed to hydrate {ticker}: {e}")
            return False
