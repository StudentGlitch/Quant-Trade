import pandas as pd
import numpy as np
from typing import Dict, Any, List
from loguru import logger

class DataStandardizer:
    """
    Standardizes data from various providers (inspired by OpenBB).
    Ensures a consistent internal schema across Equities, Macro, and Alt-Data.
    """
    
    EQUITY_SCHEMA = ['ticker', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
    MACRO_SCHEMA = ['date', 'us_10y_yield', 'us_2y_yield', 'vix_close']
    
    @staticmethod
    def standardize_equity(df: pd.DataFrame, provider: str = "yfinance") -> pd.DataFrame:
        """Map provider columns to internal standard schema."""
        df = df.copy()
        
        # Mapping logic (expandable for AlphaVantage, Polygon, etc.)
        if provider == "yfinance":
            # Already handled in yf_client, but we ensure consistency here
            mapping = {
                'Date': 'date',
                'Close': 'close',
                'Adj Close': 'adj_close'
            }
        else:
            mapping = {}
            
        df = df.rename(columns=mapping)
        df.columns = [col.lower().replace(" ", "_") for col in df.columns]
        
        # Ensure all standard columns exist
        for col in DataStandardizer.EQUITY_SCHEMA:
            if col not in df.columns:
                df[col] = np.nan
                
        return df[DataStandardizer.EQUITY_SCHEMA]

    @staticmethod
    def calculate_fundamental_ratios(ohlcv_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Synthesize 'OpenBB-style' fundamental features from price data.
        In Phase 2, this will merge with real fundamental data (P/E, Debt/Equity).
        """
        df = ohlcv_df.copy().sort_values('date')
        
        # 1. Price-to-Moving-Average (Proxy for valuation)
        df['ratio_p_ma200'] = df['adj_close'] / df['adj_close'].rolling(window=200).mean()
        
        # 2. Volume Trend (OpenBB style volume analysis)
        df['ratio_vol_ma20'] = df['volume'] / df['volume'].rolling(window=20).mean()
        
        return df
