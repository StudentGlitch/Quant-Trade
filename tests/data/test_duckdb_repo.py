from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Mock modules to bypass dependency missing in dev environment
sys.modules['duckdb'] = Mock()
sys.modules['loguru'] = Mock()

from src.data.duckdb_repo import DuckDBRepo  # noqa: E402

@patch('src.data.duckdb_repo.logger')
def test_duckdb_repo_close_exception_handling(mock_logger):
    # Setup
    # Patch Path to avoid mkdir creating actual directories during the test
    with patch('src.data.duckdb_repo.Path'):
        repo = DuckDBRepo(':memory:')

    mock_con = Mock()
    repo.con = mock_con

    # Force con.close() to raise an exception
    test_exception = Exception("Mocked database error")
    mock_con.close.side_effect = test_exception

    # Execute
    repo.close()

    # Assert
    # Check that logger.warning was called with the correct message
    mock_logger.warning.assert_called_once_with(f"Failed to close DuckDB connection cleanly: {test_exception}")

    # Verify that the connection remains unchanged since exception occurred
    # before setting self.con = None
    assert repo.con is mock_con

    # Verify that con.close() was actually called
    mock_con.close.assert_called_once()
