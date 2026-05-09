import sys
import types
from unittest.mock import MagicMock, patch

# Mock all dependencies missing in the environment before importing
for mod in ['pandas_datareader', 'pandas_datareader.data', 'yfinance', 'pandas', 'numpy', 'loguru', 'duckdb']:
    sys.modules[mod] = MagicMock()

import pandas as pd
import numpy as np

# We also need to mock DuckDBRepo to avoid importing duckdb if it's in the repo
sys.modules['src.data.duckdb_repo'] = MagicMock()

from src.data.macro_client import MacroClient

class MockDuckDBRepo:
    pass

def test_merge_and_validate():
    repo = MockDuckDBRepo()
    client = MacroClient(repo)

    # 1. Setup mock FRED DataFrame
    # Dates: Day 1, Day 2, Day 4 (skips Day 3)
    fred_data = MagicMock()

    # 2. Setup mock VIX DataFrame
    # Dates: Day 1, Day 3, Day 4 (skips Day 2)
    vix_data = MagicMock()

    # Create a mock for the joined dataframe
    joined_df = MagicMock()
    fred_data.join.return_value = joined_df

    # Create a mock for the ffilled dataframe
    ffilled_df = MagicMock()
    joined_df.ffill.return_value = ffilled_df

    # Create a mock for the dropna dataframe
    dropna_df = MagicMock()
    ffilled_df.dropna.return_value = dropna_df

    # Create a mock for the reset_index dataframe
    reset_index_df = MagicMock()
    dropna_df.reset_index.return_value = reset_index_df

    # Mock the to_datetime chain
    dt_mock = MagicMock()
    pd.to_datetime.return_value = dt_mock
    dt_mock.dt.date = "MOCKED_DATE"

    # Call method
    result_df = client._merge_and_validate(fred_data, vix_data)

    # 4. Assertions
    fred_data.join.assert_called_once_with(vix_data, how='outer')
    joined_df.ffill.assert_called_once()
    ffilled_df.dropna.assert_called_once()
    dropna_df.reset_index.assert_called_once()

    assert result_df is reset_index_df

def test_fetch_fred_data():
    repo = MockDuckDBRepo()
    client = MacroClient(repo)

    with patch('src.data.macro_client.web.DataReader') as mock_reader:
        mock_df = MagicMock()
        mock_reader.return_value = mock_df
        mock_renamed_df = MagicMock()
        mock_df.rename.return_value = mock_renamed_df

        res = client._fetch_fred_data('2023-01-01')

        mock_reader.assert_called_once_with(['DGS10', 'DGS2', 'CPIAUCSL', 'M2SL'], 'fred', '2023-01-01')
        mock_df.rename.assert_called_once_with(columns={
            'DGS10': 'us_10y_yield',
            'DGS2': 'us_2y_yield',
            'CPIAUCSL': 'us_cpi',
            'M2SL': 'us_m2'
        })
        assert res == mock_renamed_df

def test_fetch_vix_data():
    repo = MockDuckDBRepo()
    client = MacroClient(repo)

    with patch('src.data.macro_client.yf.download') as mock_download:
        mock_df = MagicMock()
        mock_download.return_value = mock_df

        # Ensure isinstance(vix.columns, pd.MultiIndex) returns False for simple test
        with patch('src.data.macro_client.isinstance', return_value=False):
            mock_sliced_df = MagicMock()
            mock_df.__getitem__.return_value = mock_sliced_df
            mock_renamed_df = MagicMock()
            mock_sliced_df.rename.return_value = mock_renamed_df

            res = client._fetch_vix_data('2023-01-01')

            mock_download.assert_called_once_with('^VIX', start='2023-01-01', auto_adjust=True, progress=False)
            mock_df.__getitem__.assert_called_once_with(['Close'])
            mock_sliced_df.rename.assert_called_once_with(columns={'Close': 'vix_close'})
            assert res == mock_renamed_df
