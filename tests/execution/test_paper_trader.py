import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.execution.paper_trader import PaperTrader


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def paper_trader_di(mock_repo):
    return PaperTrader(repo=mock_repo, model=MagicMock())


def test_initialization_no_model(mock_repo):
    with pytest.raises(ValueError, match="Must provide either model_path or model"):
        PaperTrader(repo=mock_repo)


@patch("src.execution.paper_trader.joblib.load")
def test_generate_signals_thresholds_and_feature_columns(mock_joblib_load, mock_repo):
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([0.006, -0.006, 0.002, 0.0])
    mock_joblib_load.return_value = mock_model

    trader = PaperTrader(repo=mock_repo, model_path="dummy_path.joblib")

    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "GOOG", "AMZN"],
            "feat_1": [1, 2, 3, 4],
            "feat_2": [0.1, 0.2, 0.3, 0.4],
            "other_col": ["A", "B", "C", "D"],
        }
    )

    signals = trader.generate_signals(df)

    called_df = mock_model.predict.call_args[0][0]
    assert list(called_df.columns) == ["feat_1", "feat_2"]

    assert len(signals) == 2
    assert signals[0]["ticker"] == "AAPL"
    assert signals[0]["direction"] == 1
    assert signals[1]["ticker"] == "MSFT"
    assert signals[1]["direction"] == -1


def test_generate_signals_empty_dataframe(paper_trader_di):
    df = pd.DataFrame()
    signals = paper_trader_di.generate_signals(df)
    assert signals == []
    paper_trader_di.model.predict.assert_not_called()


def test_generate_signals_missing_features(paper_trader_di):
    df = pd.DataFrame({"ticker": ["AAPL"], "no_feat_col": [100]})

    with pytest.raises(
        ValueError,
        match="No feature columns \\(starting with 'feat_'\\) found in input data.",
    ):
        paper_trader_di.generate_signals(df)


def test_generate_signals_nan_values(paper_trader_di):
    df = pd.DataFrame({"ticker": ["AAPL"], "feat_rsi": [np.nan]})

    with pytest.raises(ValueError, match="Input features contain NaN values."):
        paper_trader_di.generate_signals(df)


@patch("src.execution.paper_trader.datetime")
def test_generate_signals_signal_structure(mock_datetime, paper_trader_di):
    paper_trader_di.model.predict.return_value = np.array([0.006, -0.006])
    fixed_date = datetime(2023, 1, 1).date()
    mock_datetime.now.return_value.date.return_value = fixed_date

    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "feat_rsi": [60, 40],
        }
    )

    signals = paper_trader_di.generate_signals(df)

    assert signals[0] == {
        "ticker": "AAPL",
        "direction": 1,
        "predicted_return": 0.006,
        "signal_date": fixed_date,
    }
    assert signals[1] == {
        "ticker": "MSFT",
        "direction": -1,
        "predicted_return": -0.006,
        "signal_date": fixed_date,
    }
