import pandas as pd
import numpy as np

class AlternativeFeatures:
    """
    Feature engineering for Alternative Data (PRD Phase 2).
    Calculates Attention Spikes and Trend Momentum.
    """
    @staticmethod
    def add_attention_spikes(df: pd.DataFrame) -> pd.DataFrame:
        """Add public attention spike metrics (current / moving average)."""
        df = df.copy().sort_values('date')
        
        # 1. Wiki Views Spike (Current / 20-day MA)
        if 'wiki_views' in df.columns:
            df['wiki_views'] = df['wiki_views'].ffill()
            df['feat_wiki_spike_20d'] = df['wiki_views'] / df['wiki_views'].rolling(window=20).mean()
        
        # 2. Google Trends Momentum (Current / 20-day MA)
        if 'google_trends_score' in df.columns:
            df['google_trends_score'] = df['google_trends_score'].ffill()
            df['feat_google_momentum_20d'] = df['google_trends_score'] / df['google_trends_score'].rolling(window=20).mean()

        # Handle NaNs and clip extreme spikes
        for col in ['feat_wiki_spike_20d', 'feat_google_momentum_20d']:
            if col in df.columns:
                df[col] = df[col].replace([np.inf, -np.inf], 1.0).fillna(1.0)
                df[col] = df[col].clip(0, 10) # Cap spikes at 10x normal
        
        # 3. Rate of Change (ROC) for stationary public perception (PRD 3.4)
        if 'google_trends_score' in df.columns:
            df['feat_google_roc_5d'] = df['google_trends_score'].pct_change(periods=5).replace([np.inf, -np.inf], 0).fillna(0)
            
        return df
