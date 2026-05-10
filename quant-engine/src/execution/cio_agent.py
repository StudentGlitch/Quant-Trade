import pandas as pd
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo
from ..api.core.push_alerts import VAPIDPushService

class CIOAgent:
    """
    Phase 6.2 & 13.2: The CIO Overseer with Push Alerts.
    Acts as the ultimate risk arbiter with Kill Switch authority (PRD 7.2).
    """
    
    LIMIT_CVAR = -0.05 # 5% daily expected shortfall limit

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self.push_service = VAPIDPushService()

    def evaluate_risk_override(self) -> bool:
        """
        Evaluate tail-risk metrics and determine if the Kill Switch should be engaged.
        """
        logger.info("CIO Agent: Evaluating fund-level tail risk...")
        
        try:
            # Read latest risk metrics
            risk_row = self.repo.execute("""
                SELECT portfolio_cvar_99, volatility_regime 
                FROM risk_metrics_ledger 
                ORDER BY date DESC LIMIT 1
            """).fetchone()
            
            if not risk_row:
                logger.warning("No risk metrics found. CIO cannot evaluate override.")
                return False
                
            cvar_99, regime = risk_row
            
            kill_switch = False
            target_cash = 0.0
            
            # Rule: If CVaR99 < LimitCVaR, regime is CRISIS and Kill Switch engages
            if cvar_99 < self.LIMIT_CVAR or regime == 'CRISIS':
                logger.critical(f"TAIL RISK BREACH: CVaR99 ({cvar_99:.4f}) < Limit ({self.LIMIT_CVAR}). Engaging Kill Switch!")
                kill_switch = True
                target_cash = 1.0 # 100% Cash
                
                # Phase 13.2: Blast VAPID notification
                reason = f"CVaR breached limit: {cvar_99*100:.1f}%"
                self.push_service.send_kill_switch_alert(reason)
                
            # Update the ledger with CIO decision
            self.repo.execute("""
                UPDATE risk_metrics_ledger 
                SET cio_override_active = ?, target_cash_buffer = ?
                WHERE date = (SELECT MAX(date) FROM risk_metrics_ledger)
            """, [kill_switch, target_cash])
            
            return kill_switch
            
        except Exception as e:
            logger.error(f"CIO evaluation failed: {e}")
            return False

    def is_override_active(self) -> bool:
        """Check if an active override is in place."""
        res = self.repo.execute("SELECT cio_override_active FROM risk_metrics_ledger ORDER BY date DESC LIMIT 1").fetchone()
        return res[0] if res else False
