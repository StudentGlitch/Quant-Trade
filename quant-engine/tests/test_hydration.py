import pytest
import pandas as pd
import numpy as np
from src.data.corporate_actions import CorporateActions
from src.features.data_cleanser import DataCleanser

def test_split_adjustment_math():
    """
    Assert that adjusted_close correctly normalizes history prior to a split.
    Mock scenario: Stock drops from 10,000 to 2,000 with a 1:5 split.
    """
    dates = pd.date_range(start="2024-01-01", periods=3)
    df = pd.DataFrame({
        'date': dates,
        'open': [10000.0, 10000.0, 2000.0],
        'high': [10000.0, 10000.0, 2000.0],
        'low': [10000.0, 10000.0, 2000.0],
        'close': [10000.0, 10000.0, 2000.0],
        'volume': [100, 100, 500]
    })
    
    # 1:5 split on the last day (ratio = 5.0)
    # yfinance usually gives split on the day it occurs
    splits = pd.Series({dates[2]: 5.0})
    
    result = CorporateActions.adjust_splits(df, splits)
    
    # The prices on the first two days should now be 2,000
    assert result.iloc[0]['adjusted_close'] == 2000.0
    assert result.iloc[1]['adjusted_close'] == 2000.0
    # Today's price remains 2,000
    assert result.iloc[2]['adjusted_close'] == 2000.0
    
    # Volume on first two days should be 100 * 5 = 500
    assert result.iloc[0]['volume'] == 500

def test_ara_arb_lock_detection():
    df = pd.DataFrame({
        'open': [100.0, 100.0],
        'high': [100.0, 105.0],
        'low': [100.0, 95.0]
    })
    result = DataCleanser.detect_limit_locks(df)
    
    assert result.iloc[0]['ara_arb_lock'] == True # Flatline
    assert result.iloc[1]['ara_arb_lock'] == False # Normal candle

def test_bounded_imputation():
    """Ensure ffill stops after 5 days."""
    dates = pd.date_range(start="2024-01-01", periods=10)
    df = pd.DataFrame({
        'date': dates,
        'close': [100.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 110.0, 110.0, 110.0],
        'volume': [100, 0, 0, 0, 0, 0, 0, 100, 100, 100],
        'open': [100.0]*10, 'high': [100.0]*10, 'low': [100.0]*10, 'adjusted_close': [100.0]*10
    })
    
    result = DataCleanser.impute_missing_data(df, max_gap=5)
    
    # Row 1 is kept.
    # Rows 2-7 are 6 days of gap. 
    # Gap size 6 > 5, so these should be dropped.
    assert len(result) == 4 # Original 1 + 3 after gap
    assert pd.Timestamp("2024-01-02") not in result['date'].values
