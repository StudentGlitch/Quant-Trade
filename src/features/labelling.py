import pandas as pd
import numpy as np
from loguru import logger

class Labelling:
    @staticmethod
    def add_target(df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
        """
        Generate target variable: Forward 5-day return (PRD 6).
        Target_t = ln(Open_{t+6} / Open_{t+1})
        """
        df = df.copy().sort_values('date')
        
        # Shift Open prices to get Open_{t+1} and Open_{t+6}
        # Open_{t+1} is the next day's open
        df['open_next_1'] = df['open'].shift(-1)
        # Open_{t+6} is the open 6 days ahead
        df['open_next_6'] = df['open'].shift(-(horizon + 1))
        
        # Target: ln(Open_{t+6} / Open_{t+1})
        df['target_fwd_ret_5d'] = np.log(df['open_next_6'] / df['open_next_1'])
        
        # Binary Classification Target (PRD 5.1)
        df['target_fwd_ret_5d_bin'] = (df['target_fwd_ret_5d'] > 0).astype(int)
        
        # Cleanup temp columns
        df = df.drop(columns=['open_next_1', 'open_next_6'])
        
        return df
