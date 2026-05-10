import yfinance as yf
import pandas as pd
import numpy as np
from loguru import logger
from typing import List, Dict, Set, Tuple
from .duckdb_repo import DuckDBRepo

class UniverseFilter:
    """Pre-flight logic to purge Rp 50 zombies and illiquid stocks (PRD Phase 0.2)."""
    def __init__(self, repo: DuckDBRepo, min_adv: int = 1000000, min_price: float = 50.0):
        self.repo = repo
        self.min_adv = min_adv
        self.min_price = min_price

    def filter_universe(self, raw_tickers: Set[str], index_data: Dict[str, Set[str]]):
        """Batch download 1mo data and filter."""
        tickers_list = list(raw_tickers)
        chunk_size = 50
        
        logger.info(f"Starting Pre-Flight Check for {len(tickers_list)} tickers...")
        
        results = []
        for i in range(0, len(tickers_list), chunk_size):
            chunk = tickers_list[i:i + chunk_size]
            logger.info(f"Processing chunk {i//chunk_size + 1}/{(len(tickers_list) + chunk_size - 1)//chunk_size}...")
            
            try:
                # 2. Batch download 1mo data
                # Using auto_adjust=False because we just need close/volume
                # We group by ticker if multi-index is returned
                df = yf.download(chunk, period="1mo", progress=False)
                
                if df.empty:
                    logger.warning(f"No data returned for chunk starting with {chunk[0]}")
                    for ticker in chunk:
                        results.append(self._create_metadata_row(ticker, 'UNKNOWN', 0, index_data))
                    continue

                if isinstance(df.columns, pd.MultiIndex):
                    # Pivot to long format for easier processing
                    df = df.stack(level='Ticker', future_stack=True).reset_index()
                    # Standardize column names
                    df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
                    
                    if 'ticker' not in df.columns:
                        # Should not happen, but fallback
                        continue

                    for ticker, group in df.groupby('ticker'):
                        status, avg_vol = self._analyze_ticker_data(ticker, group)
                        results.append(self._create_metadata_row(ticker, status, avg_vol, index_data))
                else:
                    # Single ticker case
                    if len(chunk) == 1:
                        ticker = chunk[0]
                        df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
                        status, avg_vol = self._analyze_ticker_data(ticker, df)
                        results.append(self._create_metadata_row(ticker, status, avg_vol, index_data))

            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                for ticker in chunk:
                    results.append(self._create_metadata_row(ticker, 'ERROR', 0, index_data))

        # 4. Upsert results to DuckDB idx_metadata table
        self._upsert_metadata(results)
        
    def _analyze_ticker_data(self, ticker: str, df: pd.DataFrame) -> Tuple[str, int]:
        """Apply mathematical Zombie/ADV filters."""
        if df.empty or 'close' not in df.columns or 'volume' not in df.columns:
            return 'NODATA', 0
            
        closes = df['close'].dropna()
        volumes = df['volume'].dropna()
        
        if len(closes) == 0 or len(volumes) == 0:
            return 'NODATA', 0
            
        # Variance (Flatline Detection)
        # We use sample variance (ddof=1)
        variance = closes.var(ddof=1) if len(closes) > 1 else 0.0
        avg_close = closes.mean()
        avg_vol = int(volumes.mean())
        
        # PRD 6: Condition: If \sigma^2 == 0.0 AND \bar{Close} <= 51.0, status = ZOMBIE
        # Note: PRD says <= 51.0 for zombie check
        if np.isclose(variance, 0.0) and avg_close <= 51.0:
            return 'ZOMBIE', avg_vol
            
        # PRD 6: Average Daily Volume (ADV)
        if avg_vol < self.min_adv:
            return 'ILLIQUID', avg_vol
            
        return 'ACTIVE', avg_vol

    def _create_metadata_row(self, ticker: str, status: str, avg_vol: int, index_data: Dict[str, Set[str]]) -> dict:
        memberships = []
        for idx_name, constituents in index_data.items():
            if ticker in constituents:
                memberships.append(idx_name)
                
        return {
            'ticker': ticker,
            'company_name': '', # Would need another API to get company names reliably
            'sector': '',
            'index_membership': memberships,
            'status': status,
            'avg_daily_volume': avg_vol
        }

    def _upsert_metadata(self, results: List[dict]):
        if not results:
            return
            
        logger.info(f"Upserting {len(results)} metadata records to DuckDB...")
        
        # Format for DuckDB array insertion can be tricky, we'll convert lists to strings for simple storage
        # Or we can insert directly if DuckDB supports it.
        # Given PRD schema: index_membership VARCHAR[]
        # In Python, we can pass list of strings.
        
        df = pd.DataFrame(results)
        # Ensure correct types
        df['ticker'] = df['ticker'].astype(str)
        df['company_name'] = df['company_name'].astype(str)
        df['sector'] = df['sector'].astype(str)
        df['status'] = df['status'].astype(str)
        df['avg_daily_volume'] = df['avg_daily_volume'].astype(int)
        df['last_updated'] = pd.Timestamp.now()
        
        try:
            self.repo.execute("""
                INSERT OR REPLACE INTO idx_metadata 
                (ticker, company_name, sector, index_membership, status, avg_daily_volume, last_updated)
                SELECT ticker, company_name, sector, index_membership, status, avg_daily_volume, last_updated FROM df
            """)
            logger.success("idx_metadata table updated successfully.")
        except Exception as e:
            logger.error(f"Failed to upsert metadata: {e}")
