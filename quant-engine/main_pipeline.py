
import asyncio
import logging
import sys
from pathlib import Path

# Add directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from data_ingestion.yfinance_pull import fetch_ohlcv, save_to_duckdb
from features.feature_engineering import engineer_features
from models.train_xgboost import train_model
from backtest.vectorized_eval import run_backtest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - PIPELINE - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("orchestrator")

def run_pipeline(tickers: list):
    """Run the end-to-end quant research pipeline."""
    logger.info("Starting Quant Research Pipeline...")
    
    # 1. Ingest
    logger.info("Phase 1: Data Ingestion")
    raw_df = fetch_ohlcv(tickers)
    if raw_df.empty:
        logger.error("Ingestion failed. Exiting.")
        return
    save_to_duckdb(raw_df)
    
    # 2. Features
    logger.info("Phase 2: Feature Engineering")
    engineer_features()
    
    # 3. Train
    logger.info("Phase 3: Model Training (XGBoost)")
    train_model()
    
    # 4. Backtest
    logger.info("Phase 4: Vectorized Backtesting")
    run_backtest()
    
    logger.info("Pipeline Complete.")

if __name__ == "__main__":
    # Indonesian Top 5 and US Top 3 for a diverse test
    UNIVERSE = ["BBCA.JK", "TLKM.JK", "ASII.JK", "AAPL", "MSFT", "NVDA"]
    run_pipeline(UNIVERSE)
