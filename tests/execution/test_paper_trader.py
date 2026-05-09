import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from src.execution.paper_trader import PaperTrader

@pytest.fixture
def mock_repo():
    return MagicMock()

@pytest.fixture
def paper_trader(mock_repo, mocker):
    # Patch joblib.load to return a mock model to test both initialization paths
    mocker.patch("joblib.load", return_value=MagicMock())
    return PaperTrader(repo=mock_repo, model_path="mock_path.pkl")

@pytest.fixture
def paper_trader_di(mock_repo):
    # Setup PaperTrader using Dependency Injection
    mock_model = MagicMock()
    return PaperTrader(repo=mock_repo, model=mock_model)

def test_initialization_no_model(mock_repo):
    with pytest.raises(ValueError, match="Must provide either model_path or model"):
        PaperTrader(repo=mock_repo)

def test_generate_signals_thresholds(paper_trader_di):
    # Setup mock predictions
    # 0.006 -> Long, -0.006 -> Short, 0.001 -> Neutral
    paper_trader_di.model.predict.return_value = [0.006, -0.006, 0.001]

    df = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL"],
        "feat_rsi": [60, 40, 50]
    })

    signals = paper_trader_di.generate_signals(df)

    assert len(signals) == 2
    assert signals[0]["direction"] == 1  # AAPL Long
    assert signals[1]["direction"] == -1 # MSFT Short

def test_generate_signals_empty_dataframe(paper_trader_di):
    df = pd.DataFrame()
    signals = paper_trader_di.generate_signals(df)
    assert signals == []
    paper_trader_di.model.predict.assert_not_called()

def test_generate_signals_missing_features(paper_trader_di):
    df = pd.DataFrame({
        "ticker": ["AAPL"],
        "no_feat_col": [100]
    })

    with pytest.raises(ValueError, match="No feature columns \\(starting with 'feat_'\\) found in input data."):
        paper_trader_di.generate_signals(df)

def test_generate_signals_nan_values(paper_trader_di):
    df = pd.DataFrame({
        "ticker": ["AAPL"],
        "feat_rsi": [np.nan]
    })

    with pytest.raises(ValueError, match="Input features contain NaN values."):
        paper_trader_di.generate_signals(df)
