import pandas as pd
import numpy as np
from loguru import logger
from scipy.stats import pearsonr

class CorrelationEngine:
    """
    Phase 5.2.4: Ensures new features are orthogonal (uncorrelated).
    """
    
    @staticmethod
    def calculate_max_correlation(new_signal: pd.Series, existing_signals: pd.DataFrame) -> float:
        """
        Calculate the maximum absolute Pearson correlation against existing feature set.
        """
        if existing_signals.empty:
            return 0.0
            
        logger.info("Calculating orthogonal fitness (deflation)...")
        
        # Ensure indices match
        common_idx = new_signal.index.intersection(existing_signals.index)
        new_s = new_signal.loc[common_idx]
        ext_s = existing_signals.loc[common_idx]
        
        max_rho = 0.0
        for col in ext_s.columns:
            # Drop NaNs for the specific pair
            mask = new_s.notna() & ext_s[col].notna()
            if mask.sum() < 20: continue # Insufficient data
            
            rho, _ = pearsonr(new_s[mask], ext_s[col][mask])
            max_rho = max(max_rho, abs(rho))
            
        return max_rho
