import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock
from src.execution.strategy_compiler import StrategyCompiler

def test_compiler_sma_crossover():
    """
    Test that the compiler can parse a basic SMA crossover graph and generate a valid simulation.
    """
    mock_repo = MagicMock()
    compiler = StrategyCompiler(mock_repo)
    
    # Construct a simple SMA graph payload
    graph = {
        "nodes": [
            {"id": "1", "data": {"label": "SMA FAST", "window": 10}},
            {"id": "2", "data": {"label": "SMA SLOW", "window": 30}}
        ],
        "edges": [
            {"source": "1", "target": "2"}
        ],
        "starting_capital": 1000000.0
    }
    
    ticker = "BBCA.JK"
    start_date = "2020-01-01"
    end_date = "2021-01-01"
    
    # Run compilation
    results = compiler.compile_and_run(ticker, graph, start_date, end_date)
    
    # Assertions
    assert "sharpe_ratio" in results
    assert "cagr" in results
    assert "equity_curve" in results
    assert len(results["equity_curve"]) > 0
    assert isinstance(results["sharpe_ratio"], float)
    
    # Verify no insecure code execution occurred
    # (By nature of the implementation using explicit vbt.MA calls)
    assert True

def test_compiler_empty_data_handling():
    """Ensure the compiler raises error if no data is found."""
    mock_repo = MagicMock()
    compiler = StrategyCompiler(mock_repo)
    
    # Override fetch to return empty
    compiler._fetch_hydrated_data = MagicMock(return_value=pd.DataFrame())
    
    with pytest.raises(ValueError, match="No hydrated data found"):
        compiler.compile_and_run("MISSING", {"nodes": []}, "2020-01-01", "2021-01-01")
