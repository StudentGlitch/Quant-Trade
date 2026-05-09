import sys
import time
import uuid
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from orchestrator import QuantOrchestrator
from src.data.duckdb_repo import DuckDBRepo

def setup_mock_data(repo: DuckDBRepo, num_tickers: int = 100):
    """Generate mock feature_store data to test DB overhead."""
    # Ensure tables exist
    repo._init_schema()
    
    # Generate 100 tickers
    tickers = [f"TEST{i}" for i in range(num_tickers)]
    date = pd.Timestamp.now().date()
    
    data = []
    for ticker in tickers:
        data.append({
            'ticker': ticker,
            'date': date,
            'ret_1d': 0.01,
            'volatility_20d': 0.02,
            'rsi_14': 55.0,
            'macd_hist': 0.1,
            'atr_14_pct': 1.5,
            'z_score_ret_1m': 0.5,
            'feat_wiki_spike_20d': 1.2,
            'feat_google_momentum_20d': 1.1,
            'feat_google_roc_5d': 0.05,
            'ratio_p_ma200': 1.05,
            'ratio_vol_ma20': 1.2,
            'sentiment_score': 0.8,
            'target_fwd_ret_5d': 0.02,
            'target_fwd_ret_5d_bin': 1
        })
    df = pd.DataFrame(data)
    
    repo.con.execute("DROP TABLE IF EXISTS feature_store")
    repo.con.execute("CREATE TABLE feature_store AS SELECT * FROM df")
    
    # Generate some mock legacy paper_trades to test reflection query
    trades = []
    for ticker in tickers:
        trades.append((
            str(uuid.uuid4()), ticker, date, date, 0.5, 0.5, 0.5, 0.5, 0.5, 1, 'Bullish', 'Reasoning', 100.0, 10.0, 0.1, 'CLOSED'
        ))
    repo.con.executemany("""
        INSERT INTO paper_trades 
        (trade_id, ticker, signal_date, execution_date, ml_signal, llm_signal, ml_weight, llm_weight, final_blended_signal, final_direction, vibe, chain_of_thought, execution_price, position_size, transaction_cost, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, trades)
    print(f"Inserted {num_tickers} mock tickers into feature_store and paper_trades.")

def run_benchmark():
    db_path = str(BASE_DIR / "storage" / "db" / "quant_data_benchmark.duckdb")
    
    with DuckDBRepo(db_path) as repo:
        setup_mock_data(repo, num_tickers=100)
        
        orch = QuantOrchestrator(repo=repo)
        
        # Mock macro client
        orch.macro_client.get_macro = MagicMock(return_value=pd.DataFrame([{'date': pd.Timestamp.now().date(), 'us_10y_yield': 4.5}]))
        
        # Mock XGBoost model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.01] * 100)
        import joblib
        joblib.load = MagicMock(return_value=mock_model)
        
        # Mock LLM Agent to isolate DB overhead
        orch.llm_agent.get_signal_data = MagicMock(return_value={
            "vibe": "Bullish",
            "final_signal": 0.8,
            "chain_of_thought": "Mocked instantaneous response."
        })
        
        feature_cols = ['rsi_14', 'macd_hist', 'atr_14_pct'] # Dummy cols for test
        
        print("Starting optimized run_paper_trade benchmark...")
        start_time = time.perf_counter()
        
        orch.run_paper_trade(model_path="mock_model.pkl", feature_cols=feature_cols)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        print(f"Benchmark completed in {duration:.4f} seconds for 100 tickers.")
        print(f"Average time per ticker (DB overhead): {(duration/100)*1000:.2f} ms")

if __name__ == "__main__":
    run_benchmark()
