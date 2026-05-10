import pytest
from unittest.mock import MagicMock
import pandas as pd
from src.mlops.dpo_dataset_builder import DPODatasetBuilder

def test_dpo_formatting_logic():
    """
    Test that dpo_dataset_builder.py correctly maps a positive PnL trade to the chosen key 
    and a negative PnL trade to the rejected key.
    """
    mock_repo = MagicMock()
    builder = DPODatasetBuilder(repo=mock_repo)
    
    # Mock DuckDB response for war_room_transcripts
    mock_debates = pd.DataFrame({
        'debate_id': ['d1', 'd2'],
        'ticker': ['AAPL', 'MSFT'],
        'date': ['2024-01-01', '2024-01-02'],
        'transcript': ['Good trade AAPL', 'Bad trade MSFT'],
        'final_decision': ['STRONG_BUY', 'STRONG_BUY']
    })
    
    mock_repo.con.execute.return_value.df.return_value = mock_debates
    
    # We will patch the random.uniform function inside the method to force specific PnL outcomes
    import random
    with pytest.MonkeyPatch.context() as m:
        # Force first trade (AAPL) to be wildly profitable (+5%)
        # Force second trade (MSFT) to be wildly unprofitable (-5%)
        def mock_pnl(*args, **kwargs):
            if not hasattr(mock_pnl, "call_count"):
                mock_pnl.call_count = 0
            
            if mock_pnl.call_count == 0:
                mock_pnl.call_count += 1
                return 0.05
            return -0.05
            
        m.setattr(random, "uniform", mock_pnl)
        
        # Run dataset generation
        builder.generate_preference_dataset(min_return_threshold=0.02)
        
        # Verify executemany was called with the correct data
        assert mock_repo.con.executemany.called
        
        args, _ = mock_repo.con.executemany.call_args
        sql_query = args[0]
        dataset_entries = args[1]
        
        # Check AAPL entry (Profitable)
        aapl_entry = next(e for e in dataset_entries if e[1] == 'AAPL')
        assert aapl_entry[3] == 'Good trade AAPL' # Chosen response
        assert "disagree" in aapl_entry[4].lower() # Rejected response (mocked)
        assert aapl_entry[5] == 0.05 # Margin
        
        # Check MSFT entry (Unprofitable)
        msft_entry = next(e for e in dataset_entries if e[1] == 'MSFT')
        assert "avoid" in msft_entry[3].lower() # Chosen response (mocked)
        assert msft_entry[4] == 'Bad trade MSFT' # Rejected response
        assert msft_entry[5] == -0.05 # Margin
