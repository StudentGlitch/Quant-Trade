import pandas as pd
import joblib
import json
from loguru import logger
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from ..data.duckdb_repo import DuckDBRepo
from .portfolio_state import PortfolioState
from ..utils.json_utils import QuantJSONEncoder

class PaperTrader:
    def __init__(self, repo: DuckDBRepo, model_path: str):
        self.repo = repo
        self.model = joblib.load(model_path)
        self.state = PortfolioState(repo)
        # PRD 4: Setup log path
        self.log_file = Path(__file__).resolve().parent.parent.parent / "logs" / "paper_trade_log.jsonl"
        self.log_file.parent.mkdir(exist_ok=True)

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
                signal_data = {
                    'ticker': ticker,
                    'direction': direction,
                    'predicted_return': float(pred),
                    'signal_date': datetime.now().date()
                }
                signals.append(signal_data)
                
                # PRD 4 / SRC / Execution: Log reasoning trace to JSONL
                self._log_to_jsonl(signal_data)
                
        return signals

    def _log_to_jsonl(self, data: Dict[str, Any]):
        """Persist raw reasoning and trade data using the mandatory QuantJSONEncoder."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, cls=QuantJSONEncoder) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to JSONL ledger: {e}")

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
