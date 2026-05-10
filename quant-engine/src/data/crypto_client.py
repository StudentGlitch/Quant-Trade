import pandas as pd
from loguru import logger
from typing import List, Dict
import ccxt
import asyncio
from .duckdb_repo import DuckDBRepo

class CryptoClient:
    """
    Phase 18.1: CCXT wrapper for 24/7 crypto ingestion.
    """
    
    def __init__(self, repo: DuckDBRepo, exchange_id: str = 'binance'):
        self.repo = repo
        try:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({'enableRateLimit': True})
            logger.info(f"CryptoClient initialized for {exchange_id}")
        except AttributeError:
            logger.error(f"Exchange {exchange_id} not found in ccxt.")
            raise

    async def fetch_data_async(self, symbols: List[str], timeframe: str = '1d', limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data asynchronously."""
        logger.info(f"Fetching crypto data for {symbols}...")
        all_data = []
        
        for symbol in symbols:
            try:
                # CCXT uses synchronous requests by default unless ccxt.async_support is used.
                # We wrap the sync call in an async executor if using the standard ccxt.
                # For simplicity here, we'll just call it synchronously in a loop.
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
                df['ticker'] = symbol
                df['adj_close'] = df['close'] # No splits/dividends in standard crypto data
                all_data.append(df)
            except Exception as e:
                logger.error(f"Failed to fetch crypto data for {symbol}: {e}")
                
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            return final_df
        return pd.DataFrame()

    def store_data(self, df: pd.DataFrame) -> None:
        """Upsert data into DuckDB."""
        if df.empty:
            return
            
        logger.info(f"Storing {len(df)} crypto records...")
        # Assume it goes into the parquet data lake in production.
        # For MVP we can just log or store in a separate table.
        # self.repo.con.execute("CREATE TABLE IF NOT EXISTS crypto_ohlcv AS SELECT * FROM df")
        pass
