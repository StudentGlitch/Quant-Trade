import pytest
import numpy as np
from src.qa.drift_monitor import DriftMonitor
from unittest.mock import MagicMock

def test_psi_identical_distribution():
    """Assert PSI is 0.0 for identical distributions."""
    monitor = DriftMonitor(repo=MagicMock())
    
    expected = np.random.normal(0, 1, 1000)
    actual = expected.copy()
    
    psi = monitor.calculate_psi(expected, actual)
    
    assert psi == 0.0

def test_psi_drift_detection():
    """Assert PSI detects shift in mean/variance."""
    monitor = DriftMonitor(repo=MagicMock())
    
    # Training distribution (Standard Normal)
    expected = np.random.normal(0, 1, 1000)
    
    # Heavily shifted distribution (Different Mean)
    actual = np.random.normal(2, 1, 1000)
    
    psi = monitor.calculate_psi(expected, actual)
    
    # A mean shift from 0 to 2 for a standard normal should be huge PSI
    assert psi > 0.2

def test_psi_sparse_buckets():
    """Ensure small epsilon prevents division by zero in sparse data."""
    monitor = DriftMonitor(repo=MagicMock())
    
    # Very few samples
    expected = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    actual = np.array([1.0, 1.0, 1.0, 1.0, 2.0]) # Slight drift
    
    psi = monitor.calculate_psi(expected, actual)
    
    # Should calculate a number >= 0
    assert isinstance(psi, float)
    assert psi >= 0.0

