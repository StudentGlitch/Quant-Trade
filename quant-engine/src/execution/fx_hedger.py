import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime

class FxHedger:
    """
    Phase 18.2: Calculates required currency offsets (Minimum Variance Hedge Ratio).
    """

    def __init__(self, repo):
        self.repo = repo

    def calculate_hedge_ratio(self, asset_returns: pd.Series, fx_returns: pd.Series) -> float:
        """
        h* = rho * (sigma_asset / sigma_fx)
        """
        # Ensure aligned indices
        aligned = pd.concat([asset_returns, fx_returns], axis=1).dropna()
        if aligned.empty or len(aligned) < 30:
            logger.warning("Insufficient data to calculate hedge ratio. Defaulting to 1.0 (Full Hedge).")
            return 1.0
            
        rho = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])
        sigma_asset = aligned.iloc[:, 0].std()
        sigma_fx = aligned.iloc[:, 1].std()
        
        if sigma_fx == 0:
            return 1.0
            
        h_star = rho * (sigma_asset / sigma_fx)
        return float(h_star)

    def generate_hedge_orders(self, portfolio_weights: dict, base_currency: str = 'IDR') -> dict:
        """
        Calculates required FX derivative offsets for a portfolio.
        """
        logger.info(f"Generating FX hedges for base currency {base_currency}")
        
        hedge_orders = {}
        # Fetch metadata to know currency of each ticker
        try:
            meta_df = self.repo.con.execute("SELECT ticker, currency FROM global_market_metadata").df()
            meta_map = dict(zip(meta_df['ticker'], meta_df['currency']))
        except Exception:
            meta_map = {}
            
        # Group exposure by currency
        exposure_by_ccy = {}
        for ticker, weight in portfolio_weights.items():
            ccy = meta_map.get(ticker, base_currency) # Default to base if unknown
            if ccy != base_currency:
                exposure_by_ccy[ccy] = exposure_by_ccy.get(ccy, 0.0) + weight
                
        # Calculate offsets
        for ccy, exposure in exposure_by_ccy.items():
            if exposure == 0: continue
            
            # Fetch returns for asset and FX
            # Placeholder: In prod, fetch actual returns from DuckDB
            asset_ret = pd.Series(np.random.normal(0, 0.02, 100)) 
            fx_ret = pd.Series(np.random.normal(0, 0.005, 100))
            
            h_star = self.calculate_hedge_ratio(asset_ret, fx_ret)
            
            # Cap hedge ratio between 0 and 1.5
            h_star = np.clip(h_star, 0.0, 1.5)
            
            hedge_notional = exposure * h_star
            hedge_orders[f"{base_currency}_{ccy}_HEDGE"] = -hedge_notional
            
            # Log to DB
            self.repo.con.execute("""
                INSERT OR REPLACE INTO fx_hedging_ledger 
                (date, portfolio_id, base_currency, target_currency, gross_exposure, hedge_ratio, realized_fx_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [datetime.now().date(), "GLOBAL_MACRO_FUND", base_currency, ccy, float(exposure), float(h_star), 0.0])
            
            logger.info(f"Generated FX Hedge for {ccy}: Notional {hedge_notional:.2f} (Ratio: {h_star:.2f})")
            
        return hedge_orders
