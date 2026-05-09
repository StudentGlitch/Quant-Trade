import pandas as pd
import joblib
from loguru import logger
from typing import List, Dict
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo
from .portfolio_state import PortfolioState

class PaperTrader:
    def __init__(self, repo: DuckDBRepo, model_path: str):
        self.repo = repo
        self.model = joblib.load(model_path)
        self.state = PortfolioState(repo)

    def generate_signals(self, latest_features: pd.DataFrame) -> List[Dict]:
        """Perform inference and generate signals (PRD 7 Phase 5.2)."""
        logger.info("Generating signals for paper trading...")
        
        feature_cols = [col for col in latest_features.columns if col.startswith('feat_')]
        preds = self.model.predict(latest_features[feature_cols])
        
        signals = []
        for i, ticker in enumerate(latest_features['ticker']):
            pred = preds[i]
            # Thresholding (PRD 7.4.2 / 7.5.2)
            # Regressor logic: Long if > 0.5%, Short if < -0.5%
            direction = 1 if pred > 0.005 else (-1 if pred < -0.005 else 0)
            
            if direction != 0:
                signals.append({
                    'ticker': ticker,
                    'direction': direction,
                    'predicted_return': pred,
                    'signal_date': datetime.now().date()
                })
                
        return signals

    def execute(self, signals: List[Dict]):
        """Update ledger with hypothetical trades (PRD 7 Phase 5.3)."""
        available_cash = self.state.get_available_cash()
        
        # Simple equal-weight allocation for signals
        if not signals:
            return
            
        allocation_per_trade = available_cash / len(signals)
        
        for signal in signals:
            # We assume execution at current close for simplicity in paper tracking
            # though PRD says next open, we record the signal first.
            self.state.record_trade(
                ticker=signal['ticker'],
                direction=signal['direction'],
                price=0.0, # Will be filled at next open in MTM
                size=allocation_per_trade,
                cost=0.0
            )
