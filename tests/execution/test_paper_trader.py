import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime
import sys
from pathlib import Path

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.execution.paper_trader import PaperTrader
from src.data.duckdb_repo import DuckDBRepo

@pytest.fixture
def mock_repo():
    repo = Mock(spec=DuckDBRepo)
    return repo

@pytest.fixture
def mock_model():
    model = Mock()
    # Mocking prediction to match the thresholding scenarios:
    # > 0.005 -> 1 (Long)
    # < -0.005 -> -1 (Short)
    # between -0.005 and 0.005 -> 0 (No signal)
    model.predict.return_value = np.array([0.006, -0.006, 0.002, 0.0])
    return model

@pytest.fixture
def dummy_features():
    # 4 rows to correspond to the mock model predictions
    return pd.DataFrame({
        'ticker': ['AAPL', 'MSFT', 'GOOG', 'AMZN'],
        'feat_1': [1, 2, 3, 4],
        'feat_2': [0.1, 0.2, 0.3, 0.4],
        'other_col': ['A', 'B', 'C', 'D']
    })

@patch('src.execution.paper_trader.joblib.load')
@patch('src.execution.paper_trader.PortfolioState')
def test_generate_signals(mock_portfolio_state, mock_joblib_load, mock_repo, mock_model, dummy_features):
    # Setup mocks
    mock_joblib_load.return_value = mock_model

    # Initialize trader
    trader = PaperTrader(repo=mock_repo, model_path="dummy_path.joblib")

    # Generate signals
    signals = trader.generate_signals(dummy_features)

    # Assert predict was called with only feature columns
    called_df = mock_model.predict.call_args[0][0]
    assert list(called_df.columns) == ['feat_1', 'feat_2']

    # Assert the correct signals were generated
    # AAPL -> > 0.005 -> direction 1
    # MSFT -> < -0.005 -> direction -1
    # GOOG -> 0.002 -> no signal
    # AMZN -> 0.0 -> no signal

    assert len(signals) == 2

    assert signals[0]['ticker'] == 'AAPL'
    assert signals[0]['direction'] == 1
    assert signals[0]['predicted_return'] == 0.006
    assert isinstance(signals[0]['signal_date'], type(datetime.now().date()))

    assert signals[1]['ticker'] == 'MSFT'
    assert signals[1]['direction'] == -1
    assert signals[1]['predicted_return'] == -0.006
    assert isinstance(signals[1]['signal_date'], type(datetime.now().date()))

@patch('src.execution.paper_trader.joblib.load')
@patch('src.execution.paper_trader.PortfolioState')
def test_generate_signals_empty_features(mock_portfolio_state, mock_joblib_load, mock_repo, mock_model):
    mock_model.predict.return_value = np.array([])
    mock_joblib_load.return_value = mock_model
    trader = PaperTrader(repo=mock_repo, model_path="dummy.joblib")

    empty_df = pd.DataFrame(columns=['ticker', 'feat_1'])
    signals = trader.generate_signals(empty_df)

    assert len(signals) == 0

@patch('src.execution.paper_trader.datetime')
@patch('src.execution.paper_trader.joblib.load')
@patch('src.execution.paper_trader.PortfolioState')
def test_generate_signals_verify_signal_structure(mock_portfolio_state, mock_joblib_load, mock_datetime, mock_repo, mock_model, dummy_features):
    mock_joblib_load.return_value = mock_model

    # Mock datetime to return a fixed date
    fixed_date = datetime(2023, 1, 1).date()
    mock_datetime.now.return_value.date.return_value = fixed_date

    trader = PaperTrader(repo=mock_repo, model_path="dummy.joblib")
    signals = trader.generate_signals(dummy_features)

    assert len(signals) == 2

    expected_signal_aapl = {
        'ticker': 'AAPL',
        'direction': 1,
        'predicted_return': 0.006,
        'signal_date': fixed_date
    }

    expected_signal_msft = {
        'ticker': 'MSFT',
        'direction': -1,
        'predicted_return': -0.006,
        'signal_date': fixed_date
    }

    assert signals[0] == expected_signal_aapl
    assert signals[1] == expected_signal_msft
