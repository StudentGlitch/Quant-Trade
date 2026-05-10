import pandas as pd
import numpy as np
from scipy import stats
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo

class PerformanceAttribution:
    """
    Phase 4.3: Performance Attribution.
    Calculates Alpha, Beta, Max Drawdown, and Information Ratio (PRD 7.2).
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def calculate_metrics(self):
        """Build Rp and Rb arrays and calculate institutional-grade metrics."""
        logger.info("Calculating Performance Attribution metrics...")
        
        try:
            df = self.repo.execute("SELECT * FROM daily_pnl_ledger ORDER BY date").df()
            if len(df) < 2:
                logger.warning("Insufficient data in daily_pnl_ledger for attribution.")
                return None
                
            # Calculate Returns
            df['rp'] = df['total_equity'].pct_change().fillna(0)
            df['rb'] = df['benchmark_value'].pct_change().fillna(0)
            
            rp = df['rp'].values
            rb = df['rb'].values
            
            # Beta calculation (PRD 7.2)
            # beta = Cov(Rp, Rb) / Var(Rb)
            if np.var(rb) == 0:
                beta = 1.0
            else:
                beta = np.cov(rp, rb)[0, 1] / np.var(rb)
                
            # Annualized Alpha (PRD 7.2)
            # rf = 0.06 / 252 (assume 6% annual risk-free)
            rf_daily = 0.06 / 252
            
            # Simple annualized returns
            total_return_p = (1 + rp).prod() - 1
            total_return_b = (1 + rb).prod() - 1
            
            n_days = len(df)
            ann_factor = 252 / n_days
            
            # Jensen's Alpha
            # alpha = (prod(1+rp))^(252/N) - [rf + beta * ((prod(1+rb))^(252/N) - rf)]
            # We'll use the log-based approach for stability or the direct PRD formula
            alpha_ann = ((1 + total_return_p)**ann_factor) - (0.06 + beta * (((1 + total_return_b)**ann_factor) - 0.06))
            
            # Max Drawdown
            equity = df['total_equity'].values
            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / peak
            max_dd = np.max(drawdown)
            
            # Information Ratio
            # IR = (Rp - Rb) / Vol(Rp - Rb)
            active_return = rp - rb
            tracking_error = np.std(active_return) * np.sqrt(252)
            ir = (np.mean(active_return) * 252) / (tracking_error if tracking_error != 0 else 1.0)
            
            # Win Rate
            win_rate = len(df[df['rp'] > 0]) / len(df)
            
            metrics = {
                "cumulative_return_pct": total_return_p * 100,
                "cagr_pct": (((1 + total_return_p)**ann_factor) - 1) * 100,
                "max_drawdown_pct": max_dd * 100,
                "beta_to_ihsg": beta,
                "alpha_annualized": alpha_ann,
                "information_ratio": ir,
                "win_rate_pct": win_rate * 100
            }
            
            return metrics, df
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return None
