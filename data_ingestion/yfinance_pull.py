
import yfinance as yf
import pandas as pd
import duckdb
from pathlib import Path
import logging

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "raw_data" / "quant_engine.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("data_ingestion")

def fetch_ohlcv(tickers: list, period: str = "10y", interval: str = "1d"):
    """Fetch historical OHLCV data from yfinance."""
    logger.info(f"Fetching {interval} data for {len(tickers)} tickers...")
    
    all_data = []
    for ticker in tickers:
        try:
            logger.info(f"Pulling {ticker}...")
            # auto_adjust=True ensures 'Close' is adjusted.
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                continue
            
            # Flatten multi-index if present (Recent yf returns (Price, Ticker))
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Ensure index is named correctly for reset_index
            df.index.name = 'timestamp'
            df = df.reset_index()
            df['ticker'] = ticker
            
            # Standardize column names (lowercase)
            df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
            
            # Since auto_adjust=True, 'close' is already adjusted. 
            # Features engine expects 'adj_close'.
            if 'close' in df.columns:
                df['adj_close'] = df['close']
                
            all_data.append(df)
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data, ignore_index=True)

def save_to_duckdb(df: pd.DataFrame):
    """Save DataFrame to DuckDB."""
    if df.empty:
        logger.warning("Empty DataFrame, skipping save.")
        return
        
    # Handle yfinance specific 'date' vs 'datetime'
    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})
    elif 'datetime' in df.columns:
        df = df.rename(columns={'datetime': 'timestamp'})
        
    # Connect to DuckDB
    con = duckdb.connect(str(DB_PATH))
    
    # Create or replace table
    con.execute("DROP TABLE IF EXISTS market_data")
    con.execute("CREATE TABLE market_data AS SELECT * FROM df")
    
    count = con.execute("SELECT count(*) FROM market_data").fetchone()[0]
    logger.info(f"Market data updated. Total rows in DuckDB: {count}")
    con.close()

if __name__ == "__main__":
    # Test universe: IDX Top 5 + S&P 5 Tech
    test_tickers = ["BBCA.JK", "TLKM.JK", "AAPL", "MSFT", "NVDA"]
    data = fetch_ohlcv(test_tickers)
    save_to_duckdb(data)
