import numpy as np
import pandas as pd
from loguru import logger
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class JanusBlender:
    """
    Meta-weighting layer inspired by the ATLAS-GIC framework.
    Dynamically blends trading signals from multiple cohorts (e.g., 'ML_XGBoost', 'LLM_Macro')
    based on their rolling historical accuracy (Sharpe Ratio).
    """

    MIN_WEIGHT = 0.2  # No cohort drops below 20% influence
    MAX_WEIGHT = 0.8  # No cohort dominates above 80%
    ROLLING_WINDOW = 30  # Days for rolling accuracy calculation

    def __init__(self, cohorts: List[str] = None):
        self.cohorts = cohorts or ["ML_XGBoost", "LLM_Macro"]
        self.cohort_weights = {c: 1.0 / len(self.cohorts) for c in self.cohorts}
        self.history = pd.DataFrame(columns=['date', 'cohort', 'signal', 'actual_return'])

    def update_history(self, date: datetime.date, cohort: str, signal: float, actual_return: float):
        """Record the performance of a cohort's signal."""
        new_row = pd.DataFrame([{
            'date': date,
            'cohort': cohort,
            'signal': signal,
            'actual_return': actual_return,
            # Strategy return: +1 signal on +2% return = +2%. -1 signal on -2% return = +2%.
            'strategy_return': signal * actual_return 
        }])
        self.history = pd.concat([self.history, new_row], ignore_index=True)

    def _calculate_rolling_sharpe(self, cohort: str, current_date: datetime.date) -> float:
        """Calculate annualized Sharpe for a cohort over the rolling window."""
        cutoff_date = current_date - timedelta(days=self.ROLLING_WINDOW)
        
        cohort_history = self.history[
            (self.history['cohort'] == cohort) & 
            (self.history['date'] >= cutoff_date) &
            (self.history['date'] < current_date)
        ]

        if len(cohort_history) < 5:
            return 0.0 # Not enough history

        returns = cohort_history['strategy_return']
        if returns.std() == 0:
            return 0.0
            
        # Annualized Sharpe assuming daily returns
        return (returns.mean() / returns.std()) * np.sqrt(252)

    def update_weights(self, current_date: datetime.date) -> None:
        """
        Janus Darwinian Blender (PRD 6).
        Calculates weights based on 30-day rolling Sharpe ratios for both cohorts.
        Math: W_raw_ML = max(S_ML, 0) / (max(S_ML, 0) + max(S_LLM, 0))
        """
        sharpes: Dict[str, float] = {}
        for cohort in self.cohorts:
            sharpes[cohort] = self._calculate_rolling_sharpe(cohort, current_date)

        # PRD 6: Extract Sharpe values
        s_ml: float = sharpes.get("ML_XGBoost", 0.0)
        s_llm: float = sharpes.get("LLM_Macro", 0.0)
        
        # Softmax-style distribution of the positive Sharpes
        pos_s_ml: float = max(s_ml, 0.0)
        pos_s_llm: float = max(s_llm, 0.0)
        
        total_positive_sharpe: float = pos_s_ml + pos_s_llm

        if total_positive_sharpe > 0:
            # PRD 4: Softmax-style distribution
            w_raw_ml: float = pos_s_ml / total_positive_sharpe
            # PRD 3.5: Strict clamping [0.2, 0.8] to prevent single-cohort collapse
            w_ml: float = max(0.2, min(0.8, w_raw_ml))
        else:
            # PRD 6: If both are negative, revert to 0.5
            w_ml = 0.5
            
        self.cohort_weights["ML_XGBoost"] = w_ml
        self.cohort_weights["LLM_Macro"] = 1.0 - w_ml
        
        logger.info(f"Janus Weights (Sharpes ML:{s_ml:.2f} LLM:{s_llm:.2f}) -> Allocation: {self.cohort_weights}")

    def blend_signals(self, signals: Dict[str, float]) -> float:
        """
        Blend signals from multiple cohorts using current weights.
        Args:
            signals: Dict of {cohort_name: signal_value (-1.0 to 1.0)}
        Returns:
            Blended signal value (-1.0 to 1.0)
        """
        blended_signal = 0.0
        for cohort, signal in signals.items():
            weight = self.cohort_weights.get(cohort, 0.0)
            blended_signal += signal * weight
            
        return np.clip(blended_signal, -1.0, 1.0)
