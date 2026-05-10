import pandas as pd
import numpy as np
from loguru import logger
from datetime import timedelta

class CrossMarketSpillover:
    """
    Phase 18.2: Calculates lagged international alpha (Contagion Alpha).
    """

    def __init__(self, repo):
        self.repo = repo

    def calculate_lagged_spillover(self, source_df: pd.DataFrame, target_df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
        """
        Calculates Feat_spillover = Corr(R_source_t-1, R_target_t) * R_source_latest
        Ensures strict timezone shift to prevent lookahead bias.
        """
        logger.info("Calculating Cross-Market Spillover...")
        
        if source_df.empty or target_df.empty:
            logger.warning("Empty dataframe provided for spillover calculation.")
            return target_df

        # 1. Calculate Daily Returns
        source_df = source_df.sort_values('date').copy()
        target_df = target_df.sort_values('date').copy()
        
        source_df['ret_source'] = source_df['close'].pct_change()
        target_df['ret_target'] = target_df['close'].pct_change()
        
        # 2. Shift source returns by 1 day (T-1) to prevent look-ahead bias
        # This simulates closing the US market, and trading the IDX open the next morning.
        source_df['date_target'] = source_df['date'] + timedelta(days=1)
        source_shifted = source_df[['date_target', 'ret_source']].rename(columns={'date_target': 'date'})
        
        # 3. Merge on target date
        merged = pd.merge(target_df, source_shifted, on='date', how='left')
        
        # 4. Calculate Rolling Correlation
        # Corr(R_US_t-1, R_IDX_t)
        merged['lagged_corr'] = merged['ret_target'].rolling(window=window).corr(merged['ret_source'])
        
        # 5. Calculate final Spillover Feature
        # Spillover = Corr * Latest Source Return
        merged['feat_cross_market_spillover'] = merged['lagged_corr'] * merged['ret_source']
        merged['feat_cross_market_spillover'] = merged['feat_cross_market_spillover'].fillna(0.0)
        
        logger.success("Spillover feature calculated successfully.")
        return merged
