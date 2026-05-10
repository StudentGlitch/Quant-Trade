import pandas as pd
import numpy as np
from typing import List

class StatisticalFeatures:
    @staticmethod
    def add_returns_and_vol(df: pd.DataFrame) -> pd.DataFrame:
        """Add log returns and annualized 20-day volatility (PRD 6)."""
        df = df.copy().sort_values('date')
        
        # Log Returns (PRD 6)
        df['ret_1d'] = np.log(df['adj_close'] / df['adj_close'].shift(1))
        
        # Annualized 20-day Volatility (PRD 6)
        # 252 * sqrt(1/19 * sum(R - R_bar)^2) which is just daily std * sqrt(252)
        df['volatility_20d'] = df['ret_1d'].rolling(window=20).std() * np.sqrt(252)
        
        return df

    @staticmethod
    def add_cross_sectional_zscore(df: pd.DataFrame, feature: str, output_name: str) -> pd.DataFrame:
        """Calculate Z-Score within the universe for the given date (PRD 6)."""
        # Calculate mean and std separately for robustness against unhashable list errors
        means = df.groupby('date')[feature].transform('mean')
        stds = df.groupby('date')[feature].transform('std')
        
        # Avoid division by zero
        df[output_name] = (df[feature] - means) / stds.replace(0, np.nan)
        return df
