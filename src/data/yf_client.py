import yfinance as yf
import pandas as pd
from loguru import logger
from typing import List, Optional
from .duckdb_repo import DuckDBRepo

class YFinanceClient:
    def __init__(self, repo: DuckDBRepo, cache_path: str = "storage/db/requests_cache.sqlite"):
        self.repo = repo
        # Removed requests_cache as it conflicts with curl_cffi needed for YF anti-bot

    def fetch_and_store(self, tickers: List[str], start_date: str):
        """Fetch OHLCV data and upsert into DuckDB (PRD 7 Phase 1.4)."""
        logger.info(f"Fetching data for {len(tickers)} tickers starting from {start_date}...")

        for ticker in tickers:
            try:
                # Fetch data via yfinance (default session)
                df = yf.download(
                    ticker,
                    start=start_date,
                    auto_adjust=True,
                    progress=False
                )

                if df.empty:
                    logger.warning(f"No data returned for {ticker}")
                    continue

                # Standardize columns and reset index
                if isinstance(df.columns, pd.MultiIndex):
                    # In newer yf, price is level 0, Ticker is level 1
                    df.columns = df.columns.get_level_values(0)

                df.index.name = 'date'
                df = df.reset_index()

                # Standardize names for SQL
                df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]

                # Drop duplicate columns if any
                df = df.loc[:, ~df.columns.duplicated()]

                df['ticker'] = str(ticker) # Explicitly cast to string

                # Ensure date is actual date object
                df['date'] = pd.to_datetime(df['date']).dt.date

                # Map Close to adj_close if auto_adjust was True
                if 'close' in df.columns and 'adj_close' not in df.columns:
                    df['adj_close'] = pd.to_numeric(df['close'], errors='coerce')
                elif 'adj_close' in df.columns:
                    df['adj_close'] = pd.to_numeric(df['adj_close'], errors='coerce')

                # Upsert logic (PRD 7 Phase 1.4)
                # Explicitly name columns to avoid conversion errors from mismatched order
                self.repo.con.execute("""
                    INSERT OR REPLACE INTO ohlcv_daily
                    (ticker, date, open, high, low, close, adj_close, volume)
                    SELECT ticker, date, open, high, low, close, adj_close, volume
                    FROM df
                """)
                logger.info(f"Stored {len(df)} rows for {ticker}")

            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")

    def get_ohlcv(self, ticker: str) -> pd.DataFrame:
        """Query OHLCV data from DuckDB (PRD 3.3)."""
        return self.repo.con.execute(
            "SELECT * FROM ohlcv_daily WHERE ticker = ? ORDER BY date",
            [ticker]
        ).df()

    def get_all_ohlcv(self) -> pd.DataFrame:
        """Query all OHLCV data from DuckDB."""
        return self.repo.con.execute("SELECT * FROM ohlcv_daily ORDER BY ticker, date").df()
