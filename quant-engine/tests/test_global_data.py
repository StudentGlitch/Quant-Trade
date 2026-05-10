import pytest
import pandas as pd
from datetime import datetime, timedelta
import pytz
from src.features.cross_market_spillover import CrossMarketSpillover

def test_timezone_lookahead_bias():
    """
    Ensure cross-market spillover calculation strictly aligns T-1 source with T target.
    """
    repo_mock = None
    spillover_engine = CrossMarketSpillover(repo_mock)
    
    # Mock US Data (Source)
    us_dates = pd.date_range(start="2024-10-01", periods=5, freq='B') 
    us_data = pd.DataFrame({
        'date': us_dates,
        'close': [100, 101, 105, 103, 106]
    })
    # Oct 1 (Tue): NaN
    # Oct 2 (Wed): 0.01
    # Oct 3 (Thu): 0.0396
    
    # Mock IDX Data (Target)
    idx_data = pd.DataFrame({
        'date': us_dates,
        'close': [5000, 5050, 5000, 5100, 5200]
    })
    
    # Run calculation
    result_df = spillover_engine.calculate_lagged_spillover(us_data, idx_data, window=2)
    
    # Target date '2024-10-03' (Thursday) should receive the source return from '2024-10-02' (Wednesday)
    target_row = result_df[result_df['date'] == pd.Timestamp("2024-10-03")]
    
    if not target_row.empty:
        # Wednesday US return = (101-100)/100 = 0.01
        expected_source_ret = 0.01
        actual_source_ret = target_row['ret_source'].values[0]
        assert abs(actual_source_ret - expected_source_ret) < 1e-6, "Lookahead bias detected! T-1 data not used."

