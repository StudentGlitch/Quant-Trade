import pandas as pd
from typing import Tuple, Generator

class PurgedWalkForwardCV:
    """
    Purged Walk-Forward Cross-Validation with Embargo (PRD 7 Phase 3.1).
    Prevents data leakage by ensuring no overlap between train/test including target horizon.
    """
    def __init__(self, n_splits: int = 5, embargo_period: int = 5):
        self.n_splits = n_splits
        self.embargo_period = embargo_period

    def split(self, df: pd.DataFrame) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
        """Strict chronological splitting with purging/embargo."""
        df = df.sort_values('date')
        unique_dates = sorted(df['date'].unique())
        n_dates = len(unique_dates)
        
        # Calculate split sizes
        split_size = n_dates // (self.n_splits + 1)
        
        for i in range(self.n_splits):
            train_end_idx = split_size * (i + 1)
            test_start_idx = train_end_idx + self.embargo_period
            test_end_idx = test_start_idx + split_size
            
            if test_start_idx >= n_dates:
                break
                
            train_dates = unique_dates[:train_end_idx]
            test_dates = unique_dates[test_start_idx:min(test_end_idx, n_dates)]
            
            train_df = df[df['date'].isin(train_dates)]
            test_df = df[df['date'].isin(test_dates)]
            
            yield train_df, test_df
