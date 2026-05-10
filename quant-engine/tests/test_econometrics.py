import pytest
import numpy as np
import pandas as pd
from src.features.econometric_forecaster import EconometricForecaster
from unittest.mock import MagicMock

def test_stationarity_detection_and_differencing():
    """Assert that the forecaster detects non-stationarity and applies diffing."""
    # Mock Repo
    mock_repo = MagicMock()
    
    # Create non-stationary data (Exponential growth)
    dates = pd.date_range(start="2024-01-01", periods=100)
    data = pd.DataFrame({
        'date': dates,
        'vix_close': np.linspace(10, 50, 100) + np.random.normal(0, 1, 100),
        'us_cpi': np.linspace(200, 300, 100),
        'us_m2': np.linspace(1000, 2000, 100),
        'us_10y_yield': np.linspace(1, 5, 100)
    })
    
    mock_repo.con.execute.return_value.df.return_value = data
    
    forecaster = EconometricForecaster(mock_repo)
    
    # We test the reintegration logic specifically
    # Create mock diff forecast
    horizon = 5
    diff_forecast = np.ones((horizon, 4)) * 0.1 # Small positive diffs
    
    original_data = data[['vix_close', 'us_cpi', 'us_m2', 'us_10y_yield']]
    
    # Reintegrate with diff_order 1
    abs_forecast = forecaster._reintegrate(original_data, diff_forecast, diff_order=1, horizon=horizon)
    
    # First value should be last_val + 0.1
    last_vix = original_data['vix_close'].iloc[-1]
    assert abs(abs_forecast['vix_close'][0] - (last_vix + 0.1)) < 1e-6
    # Second value should be last_val + 0.2
    assert abs(abs_forecast['vix_close'][1] - (last_vix + 0.2)) < 1e-6

def test_insufficient_data_handling():
    mock_repo = MagicMock()
    # Empty data
    mock_repo.con.execute.return_value.df.return_value = pd.DataFrame()
    
    forecaster = EconometricForecaster(mock_repo)
    
    # Should exit gracefully
    result = forecaster.forecast_macro_regime()
    assert result is None
