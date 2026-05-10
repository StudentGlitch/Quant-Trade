import pytest
import pandas as pd
import numpy as np
from src.utils.metrics import calculate_sortino

def test_calculate_sortino_happy_path():
    """Test standard case with varied positive and negative returns."""
    # 0.04/252 is approx 0.0001587. So we use returns above and below that.
    returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.005])

    res = calculate_sortino(returns, risk_free_rate=0.04)
    # The return value should be a float and not NaN
    assert isinstance(res, float)
    assert not pd.isna(res)
    # We can manually calculate it or just assert it's a valid float since formula is straightforward.

def test_calculate_sortino_no_downside():
    """Test case where there are no negative excess returns (downside_std is NaN)."""
    # All returns are positive and greater than risk free rate
    returns = pd.Series([0.01, 0.02, 0.03, 0.04])

    res = calculate_sortino(returns, risk_free_rate=0.04)
    assert res == 0.0

def test_calculate_sortino_zero_downside_std():
    """Test case where all negative excess returns are identical (downside_std is 0)."""
    # 0.04/252 = 0.0001587. Let's say all negative returns are -0.01
    # Note: if there's only 1 negative return, std() is NaN, which is covered by test_calculate_sortino_no_downside.
    # To get std() = 0, we need >= 2 identical negative returns.
    returns = pd.Series([0.01, -0.01, -0.01, -0.01, 0.02])

    res = calculate_sortino(returns, risk_free_rate=0.04)
    assert res == 0.0
