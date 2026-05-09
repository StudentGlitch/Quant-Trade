
import duckdb
import pandas as pd
import vectorbt as vbt
import joblib
import logging
from pathlib import Path
import numpy as np

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "storage" / "raw_data" / "quant_engine.db"
MODEL_PATH = BASE_DIR / "storage" / "artifacts" / "xgboost_model.pkl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backtest")

def run_backtest():
    """Evaluate model performance using vectorbt."""
    # 1. Load Model & Data
    if not MODEL_PATH.exists():
        logger.error("Model not found. Run train_xgboost.py first.")
        return
        
    model = joblib.load(str(MODEL_PATH))
    
    con = duckdb.connect(str(DB_PATH))
    df = con.execute("SELECT * FROM market_data_features ORDER BY timestamp, ticker").df()
    con.close()
    
    # 2. Get Test Data (Last 15% of dates)
    df = df.dropna(subset=[col for col in df.columns if col.startswith('feat_')])
    unique_dates = sorted(df['timestamp'].unique())
    test_start_idx = int(len(unique_dates) * 0.85)
    test_dates = unique_dates[test_start_idx:]
    
    test_df = df[df['timestamp'].isin(test_dates)].copy()
    
    # 3. Generate Signals
    feature_cols = [col for col in test_df.columns if col.startswith('feat_')]
    test_df['pred_return'] = model.predict(test_df[feature_cols])
    
    # Signal: Long if predicted return > 0.01 (1% threshold)
    test_df['signal'] = test_df['pred_return'] > 0.005
    
    # 4. Prepare for vectorbt
    # Pivot to have tickers as columns
    close_prices = test_df.pivot(index='timestamp', columns='ticker', values='adj_close')
    signals = test_df.pivot(index='timestamp', columns='ticker', values='signal')
    
    # Ensure signals are aligned with next day's open/close
    # We shift signals by 1 to avoid look-ahead bias (entering at next bar's close)
    signals = signals.shift(1).fillna(False)
    
    # 5. Run vectorbt Backtest
    portfolio = vbt.Portfolio.from_signals(
        close_prices,
        entries=signals,
        exits=~signals,
        freq='1d',
        init_cash=10000,
        fees=0.001 # 0.1% commission
    )
    
    # 6. Output Metrics
    stats = portfolio.stats()
    logger.info("\n--- Backtest Results (Test Set) ---")
    logger.info(f"Total Return: {stats['Total Return [%]']:.2f}%")
    logger.info(f"Benchmark Return: {stats['Benchmark Return [%]']:.2f}%")
    logger.info(f"Sharpe Ratio: {stats['Sharpe Ratio']:.4f}")
    logger.info(f"Max Drawdown: {stats['Max Drawdown [%]']:.2f}%")
    logger.info(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
    
    # Plotting would be nice but we are strictly headless
    # portfolio.plot().show() 

if __name__ == "__main__":
    run_backtest()
