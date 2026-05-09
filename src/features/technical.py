import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange, BollingerBands
from typing import Optional

class TechnicalFeatures:
    @staticmethod
    def add_all(df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD, RSI, ATR, and Bollinger Bands (PRD 4 Deep Architecture)."""
        df = df.copy().sort_values('date')
        
        # 1. RSI (14-day)
        df['rsi_14'] = RSIIndicator(close=df['adj_close'], window=14).rsi()
        
        # 2. MACD Histogram
        macd = MACD(close=df['adj_close'])
        df['macd_hist'] = macd.macd_diff()
        
        # 3. ATR (14-day) - Normalized by price (PRD 5.1 feature_store)
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['adj_close'], window=14)
        df['atr_14_pct'] = (atr.average_true_range() / df['adj_close']) * 100
        
        # 4. Bollinger Bands (20-day)
        bb = BollingerBands(close=df['adj_close'], window=20)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        
        return df
