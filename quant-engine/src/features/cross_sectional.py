import pandas as pd
import numpy as np
from loguru import logger
from typing import List

class CrossSectionalFeatures:
    """
    Phase 2.2: Cross-Sectional Feature Engineering
    Calculates sector-relative Z-scores for ML signals (PRD 6.1).
    """
    @staticmethod
    def calculate_sector_zscore(df: pd.DataFrame, idx_metadata: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Z-Score of the ML signal relative to the ticker's sector peers.
        """
        if df.empty or idx_metadata.empty:
            logger.warning("Empty dataframe provided for cross-sectional scoring.")
            df['cross_sectional_z_score'] = 0.0
            return df
            
        logger.info("Calculating Cross-Sectional Sector Normalization...")
        
        # Merge sector info
        working_df = df.merge(idx_metadata[['ticker', 'sector']], on='ticker', how='left')
        
        # Handle missing sectors by grouping them into 'UNKNOWN'
        working_df['sector'] = working_df['sector'].fillna('UNKNOWN')
        
        # Calculate Z-score grouped by date and sector
        # For a given day and sector, how many standard deviations away is this signal?
        def _zscore(x):
            # If standard deviation is zero (or NaN due to single item), return 0
            if len(x) <= 1 or x.std() == 0:
                return pd.Series(0.0, index=x.index)
            return (x - x.mean()) / x.std()
            
        working_df['cross_sectional_z_score'] = working_df.groupby(['date', 'sector'])['ml_pred'].transform(_zscore)
        
        # Clean up
        working_df['cross_sectional_z_score'] = working_df['cross_sectional_z_score'].fillna(0.0)
        
        # Remove the temporary sector column if it wasn't there originally
        if 'sector' not in df.columns:
            working_df = working_df.drop(columns=['sector'])
            
        return working_df
