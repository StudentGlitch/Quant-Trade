import pytest
import pandas as pd
import numpy as np

# Adjust python path if necessary or use sys.path modification to import src
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.math_utils import remove_zero_variance

def test_remove_zero_variance_normal():
    """Test with normal columns that vary."""
    df = pd.DataFrame({
        'A': [1.0, 2.0, 3.0, 4.0],
        'B': [10.0, 20.0, 15.0, 25.0]
    })
    result = remove_zero_variance(df)
    assert list(result.columns) == ['A', 'B']
    assert result.shape == (4, 2)

def test_remove_zero_variance_one_constant():
    """Test with one constant column and one normal column."""
    df = pd.DataFrame({
        'A': [1.0, 2.0, 3.0, 4.0],
        'B': [5.0, 5.0, 5.0, 5.0]
    })
    result = remove_zero_variance(df)
    assert list(result.columns) == ['A']
    assert result.shape == (4, 1)

def test_remove_zero_variance_all_constant():
    """Test where all columns are constant."""
    df = pd.DataFrame({
        'A': [1.0, 1.0, 1.0, 1.0],
        'B': [5.0, 5.0, 5.0, 5.0]
    })
    result = remove_zero_variance(df)
    assert list(result.columns) == []
    assert result.shape == (4, 0)

def test_remove_zero_variance_near_zero():
    """Test with a column that has near-zero variance (< threshold)."""
    # Create a column with very small variations
    df = pd.DataFrame({
        'A': [1.0, 2.0, 3.0, 4.0],
        'B': [5.0, 5.0 + 1e-7, 5.0, 5.0 - 1e-7]
    })

    # By default threshold is 1e-6
    # The variance of B is small enough to be removed
    result = remove_zero_variance(df)
    assert list(result.columns) == ['A']
    assert result.shape == (4, 1)

def test_remove_zero_variance_empty_df():
    """Test edge case: Empty DataFrame."""
    df = pd.DataFrame()
    result = remove_zero_variance(df)
    assert list(result.columns) == []
    assert result.shape == (0, 0)

    df_with_cols = pd.DataFrame(columns=['A', 'B'])
    result2 = remove_zero_variance(df_with_cols)
    assert list(result2.columns) == ['A', 'B']
    assert result2.shape == (0, 2)

def test_remove_zero_variance_single_row():
    """Test edge case: Single-row DataFrame."""
    df = pd.DataFrame({
        'A': [1.0],
        'B': [5.0]
    })
    # Variance of a single row is NaN. NaN < threshold is False.
    # Therefore, no columns should be removed.
    result = remove_zero_variance(df)
    assert list(result.columns) == ['A', 'B']
    assert result.shape == (1, 2)
