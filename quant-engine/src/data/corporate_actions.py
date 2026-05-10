import pandas as pd
import numpy as np
from loguru import logger

class CorporateActions:
    """
    Phase 23.2: Corporate Action Adjustment Engine.
    Handles retrospective split and dividend adjustments for continuous OHLCV.
    """

    @staticmethod
    def adjust_splits(df: pd.DataFrame, splits: pd.Series) -> pd.DataFrame:
        """
        Applies split adjustment backward from the present (PRD 7.1).
        P_adj = P_raw * cumulative_product(split_ratios)
        """
        if splits.empty:
            df['split_multiplier'] = 1.0
            df['adjusted_close'] = df['close']
            return df

        logger.info(f"Applying {len(splits)} corporate splits to history.")
        
        # 1. Create a multiplier series aligned with df index
        # We need to reverse the cumulative product to apply it backward
        # yfinance splits are usually given as (new_shares / old_shares)
        # We want to multiply historical prices by (1 / ratio) if we trade today's units
        
        # Ensure splits is a series indexed by date
        splits.index = pd.to_datetime(splits.index).date
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Map splits to the dataframe
        df = df.sort_values('date', ascending=False)
        df['split_ratio'] = df['date'].map(splits).fillna(1.0)
        
        # Cumulative product backwards
        # The multiplier for day T should be 1.0.
        # The multiplier for day T-1 is the product of all future split ratios.
        # We shift the split_ratio to ensure today's price isn't adjusted by today's split.
        df['split_multiplier'] = df['split_ratio'].shift(fill_value=1.0).cumprod()
        
        # Adjust OHLC (Price * Multiplier, Volume / Multiplier)
        df['adjusted_close'] = df['close'] / df['split_multiplier']
        df['open'] = df['open'] / df['split_multiplier']
        df['high'] = df['high'] / df['split_multiplier']
        df['low'] = df['low'] / df['split_multiplier']
        df['volume'] = (df['volume'] * df['split_multiplier']).astype(np.int64)
        
        return df.sort_values('date')

    @staticmethod
    def calculate_dividend_yield(df: pd.DataFrame, dividends: pd.Series) -> pd.DataFrame:
        """Calculate trailing dividend yield."""
        if dividends.empty:
            df['dividend_yield'] = 0.0
            return df
            
        dividends.index = pd.to_datetime(dividends.index).date
        df['div_amt'] = df['date'].map(dividends).fillna(0.0)
        
        # 12-month rolling yield
        df['dividend_yield'] = df['div_amt'].rolling(window=252, min_periods=1).sum() / df['close']
        return df.drop(columns=['div_amt'])
