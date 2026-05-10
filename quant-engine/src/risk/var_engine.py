import pandas as pd
import numpy as np
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo

class RiskEngine:
    """
    Phase 6.1: Risk Engine (Value-at-Risk & Expected Shortfall).
    Calculates VaR99 and CVaR99 from historical portfolio returns.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self._init_ledger()

    def _init_ledger(self):
        """Initialize risk_metrics_ledger table."""
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS risk_metrics_ledger (
                date DATE PRIMARY KEY,
                portfolio_var_99 DOUBLE,
                portfolio_cvar_99 DOUBLE,
                volatility_regime VARCHAR, -- 'LOW', 'NORMAL', 'HIGH', 'CRISIS'
                cio_override_active BOOLEAN DEFAULT FALSE,
                target_cash_buffer DOUBLE DEFAULT 0.0
            );
        """)

    def calculate_tail_risk(self, window: int = 252) -> dict:
        """
        Calculate VaR and CVaR using the historical method.
        PRD 7.1 mathematical requirements.
        """
        logger.info(f"Calculating tail risk (VaR/CVaR) with window={window}...")
        
        try:
            # Fetch trailing returns
            df = self.repo.execute(f"""
                SELECT total_equity 
                FROM daily_pnl_ledger 
                ORDER BY date DESC 
                LIMIT {window + 1}
            """).df()
            
            if len(df) < 10:
                logger.warning("Insufficient history for VaR calculation. Returning defaults.")
                return self._save_defaults()

            # Reverse to chronological order for returns calculation
            returns = df['total_equity'].iloc[::-1].pct_change().dropna().values
            
            if len(returns) == 0:
                return self._save_defaults()

            # 1. Value at Risk (VaR99)
            # Percentile(R, 100 * alpha) where alpha = 0.01
            var_99 = np.percentile(returns, 1)
            
            # 2. Conditional VaR (CVaR99 / Expected Shortfall)
            # Average loss given that the loss has exceeded the VaR threshold
            tail_losses = returns[returns <= var_99]
            cvar_99 = np.mean(tail_losses) if len(tail_losses) > 0 else var_99
            
            # Volatility Regime Logic
            vol_ann = np.std(returns) * np.sqrt(252)
            regime = 'NORMAL'
            if vol_ann < 0.10: regime = 'LOW'
            elif vol_ann > 0.30: regime = 'HIGH'
            
            # Override to CRISIS if CVaR breaches limit
            if cvar_99 < -0.05:
                regime = 'CRISIS'
                
            risk_data = {
                "var_99": float(var_99),
                "cvar_99": float(cvar_99),
                "regime": regime
            }
            
            self._save_to_ledger(risk_data)
            return risk_data
            
        except Exception as e:
            logger.error(f"Risk calculation failed: {e}")
            return self._save_defaults()

    def _save_to_ledger(self, data: dict):
        self.repo.execute("""
            INSERT OR REPLACE INTO risk_metrics_ledger (date, portfolio_var_99, portfolio_cvar_99, volatility_regime)
            VALUES (CURRENT_DATE, ?, ?, ?)
        """, [data['var_99'], data['cvar_99'], data['regime']])

    def _save_defaults(self):
        res = {"var_99": 0.0, "cvar_99": 0.0, "regime": "UNKNOWN"}
        self._save_to_ledger(res)
        return res
