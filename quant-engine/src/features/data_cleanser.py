import pandas as pd
import numpy as np
from loguru import logger

class DataCleanser:
    """
    Phase 23.2: IDX-Specific Data Cleansing.
    Handles NaN imputation, ARA/ARB locks, and illiquid day filtering.
    """

    @staticmethod
    def detect_limit_locks(df: pd.DataFrame) -> pd.DataFrame:
        """
        ARA/ARB Detection: Lock = True if (High - Low) < 0.001 * Open (PRD 7.2).
        """
        df['ara_arb_lock'] = (df['high'] - df['low']) < (0.001 * df['open'])
        return df

    @staticmethod
    def impute_missing_data(df: pd.DataFrame, max_gap: int = 5) -> pd.DataFrame:
        """
        Bounded Forward Fill (max 5 days). Beyond that, mark as SUSPENDED (drop).
        """
        # Identify gaps (Volume == 0 or Close is NaN)
        df['is_missing'] = (df['volume'] == 0) | (df['close'].isna())
        
        # Create a group ID for consecutive missing days
        df['gap_id'] = (df['is_missing'] != df['is_missing'].shift()).cumsum()
        
        # Calculate size of each gap
        gap_sizes = df[df['is_missing']].groupby('gap_id').size()
        
        # Filter for gaps within limit
        valid_gap_ids = gap_sizes[gap_sizes <= max_gap].index
        
        # Forward fill ONLY if it's a valid gap
        # This is a bit complex in one-liner, so we'll do it iteratively or with masking
        df['is_imputed'] = df['is_missing'] & df['gap_id'].isin(valid_gap_ids)
        
        # Perform ffill
        df[['open', 'high', 'low', 'close', 'adjusted_close']] = df[['open', 'high', 'low', 'close', 'adjusted_close']].ffill()
        df['volume'] = df['volume'].replace(0, np.nan).ffill().fillna(0)
        
        # Drop rows where gap exceeded max_gap
        df = df[~(df['is_missing'] & ~df['gap_id'].isin(valid_gap_ids))]
        
        return df.drop(columns=['is_missing', 'gap_id'])
