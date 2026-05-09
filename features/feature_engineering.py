
import pandas as pd
import numpy as np
import duckdb
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange, BollingerBands
import logging
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "raw_data" / "quant_engine.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("features")

def engineer_features():
    """Read from DuckDB, calculate technical indicators, and write back."""
    con = duckdb.connect(str(DB_PATH))
    df = con.execute("SELECT * FROM market_data ORDER BY ticker, timestamp").df()
    
    if df.empty:
        logger.error("No data found in market_data table.")
        con.close()
        return

    logger.info(f"Engineering features for {len(df)} rows...")
    
    # Process per ticker to ensure indicators are correct (not leaking between tickers)
    processed_dfs = []
    for ticker, group in df.groupby('ticker'):
        group = group.copy().sort_values('timestamp')
        
        # 1. Momentum
        group['feat_rsi_14'] = RSIIndicator(close=group['adj_close'], window=14).rsi()
        stoch_rsi = StochRSIIndicator(close=group['adj_close'], window=14)
        group['feat_stoch_rsi'] = stoch_rsi.stochrsi()
        
        # 2. Trend
        macd = MACD(close=group['adj_close'])
        group['feat_macd_hist'] = macd.macd_diff()
        
        # 3. Volatility
        group['feat_volatility_20'] = group['adj_close'].pct_change().rolling(window=20).std()
        group['feat_atr_14'] = AverageTrueRange(high=group['high'], low=group['low'], close=group['adj_close'], window=14).average_true_range()
        
        # 4. Bollinger Bands
        bb = BollingerBands(close=group['adj_close'], window=20)
        group['feat_bb_width'] = bb.bollinger_wband()
        
        # 5. TARGET: Log forward 5-day return
        # continuously compounded forward 5-day return
        group['target_fwd_return_5d'] = np.log(group['adj_close'].shift(-5) / group['adj_close'])
        
        processed_dfs.append(group)
        
    final_df = pd.concat(processed_dfs, ignore_index=True)
    
    # Save back to DuckDB (Upsert or overwrite the table with new columns)
    con.execute("DROP TABLE IF EXISTS market_data_features")
    con.execute("CREATE TABLE market_data_features AS SELECT * FROM final_df")
    
    logger.info("Features engineered and saved to market_data_features.")
    con.close()

if __name__ == "__main__":
    engineer_features()
