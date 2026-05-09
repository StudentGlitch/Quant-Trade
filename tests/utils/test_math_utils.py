import pytest
import pandas as pd
import numpy as np

from src.utils.math_utils import check_stationarity

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
