import pytest
import pandas as pd
import numpy as np

from src.utils.math_utils import cap_outliers, check_stationarity

def test_check_stationarity_stationary():
    # A random noise series should be stationary
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 100))
    assert check_stationarity(series) is True

def test_check_stationarity_non_stationary():
    # A cumulative sum series (random walk) is typically non-stationary
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 100).cumsum())
    assert check_stationarity(series) is False

def test_check_stationarity_exception():
    # Passing an invalid series type or triggering an exception
    # By passing an empty series after dropna, adfuller will raise an exception
    series = pd.Series([np.nan, np.nan])
    assert check_stationarity(series) is False
def test_cap_outliers_default_threshold():
    """Test standard clipping behavior with the default threshold (3.0)."""
    series = pd.Series([-4.5, -3.0, -1.0, 0.0, 1.5, 3.0, 5.2])
    capped = cap_outliers(series)

    # Values should be clipped between -3.0 and 3.0
    expected = pd.Series([-3.0, -3.0, -1.0, 0.0, 1.5, 3.0, 3.0])
    pd.testing.assert_series_equal(capped, expected)

def test_cap_outliers_custom_threshold():
    """Test clipping behavior with a custom threshold."""
    series = pd.Series([-10.5, -5.0, 0.0, 5.0, 10.5])
    capped = cap_outliers(series, threshold=5.0)

    # Values should be clipped between -5.0 and 5.0
    expected = pd.Series([-5.0, -5.0, 0.0, 5.0, 5.0])
    pd.testing.assert_series_equal(capped, expected)

def test_cap_outliers_with_nans():
    """Test that NaN values are correctly preserved and do not cause errors."""
    series = pd.Series([-4.0, np.nan, 2.5, 4.0, np.nan])
    capped = cap_outliers(series)

    # NaNs should remain in the same positions
    expected = pd.Series([-3.0, np.nan, 2.5, 3.0, np.nan])
    pd.testing.assert_series_equal(capped, expected)

def test_cap_outliers_with_infinity():
    """Test that infinite values are correctly clipped to the threshold."""
    series = pd.Series([-np.inf, -2.0, 0.0, 2.0, np.inf])
    capped = cap_outliers(series)

    # Infinities should be clipped to -3.0 and 3.0
    expected = pd.Series([-3.0, -2.0, 0.0, 2.0, 3.0])
    pd.testing.assert_series_equal(capped, expected)

def test_cap_outliers_empty_series():
    """Test that an empty Series is returned without error."""
    series = pd.Series([], dtype=float)
    capped = cap_outliers(series)

    expected = pd.Series([], dtype=float)
    pd.testing.assert_series_equal(capped, expected)
