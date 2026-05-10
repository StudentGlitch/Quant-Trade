import numpy as np
import pandas as pd
from loguru import logger
import math
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo

class BlackSwanEngine:
    """
    Phase 13.3: Black Swan Scenario Engine.
    Uses Merton Jump-Diffusion to stress-test the portfolio via Monte Carlo.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self._init_ledger()

    def _init_ledger(self):
        """Initialize black_swan_simulations table."""
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS black_swan_simulations (
                date DATE,
                scenario_name VARCHAR,
                simulated_drawdown_pct DOUBLE,
                survival_probability DOUBLE,
                portfolio_resilient BOOLEAN,
                PRIMARY KEY (date, scenario_name)
            );
        """)

    def run_simulations(self):
        """Run the daily Monte Carlo stress tests."""
        logger.info("Black Swan Engine: Starting Merton Jump-Diffusion simulations...")
        
        try:
            # 1. Fetch current portfolio equity
            equity_row = self.repo.execute("SELECT total_equity FROM daily_pnl_ledger ORDER BY date DESC LIMIT 1").fetchone()
            if not equity_row or equity_row[0] <= 0:
                logger.warning("No equity data for Black Swan simulation.")
                return
                
            s0 = float(equity_row[0])
            
            # 2. Define Scenarios
            scenarios = [
                {
                    "name": "IDR_CURRENCY_CRISIS",
                    "mu": 0.05 / 252, # Annualized drift
                    "sigma": 0.35 / math.sqrt(252), # High vol
                    "jump_intensity": 5 / 252, # Expected 5 jumps per year
                    "jump_mean": -0.15, # Average jump drops 15%
                    "jump_std": 0.05
                },
                {
                    "name": "GLOBAL_PANDEMIC_REPLAY",
                    "mu": -0.05 / 252,
                    "sigma": 0.50 / math.sqrt(252),
                    "jump_intensity": 10 / 252,
                    "jump_mean": -0.20,
                    "jump_std": 0.10
                },
                {
                    "name": "COMMODITY_SUPER_CYCLE_CRASH",
                    "mu": 0.02 / 252,
                    "sigma": 0.25 / math.sqrt(252),
                    "jump_intensity": 3 / 252,
                    "jump_mean": -0.10,
                    "jump_std": 0.08
                }
            ]
            
            num_paths = 10000
            days = 30
            current_date = datetime.now().date()
            
            records = []
            
            for sc in scenarios:
                res = self._simulate_merton_jump_diffusion(
                    s0, sc['mu'], sc['sigma'], sc['jump_intensity'], sc['jump_mean'], sc['jump_std'], num_paths, days
                )
                
                survival_prob = res['survival_probability']
                max_dd = res['worst_drawdown']
                resilient = bool(survival_prob > 0.95) # resilient if >95% paths survive
                
                records.append((current_date, sc['name'], max_dd, survival_prob, resilient))
                
                status_str = "PASSED" if resilient else "FAILED"
                logger.info(f"Scenario {sc['name']}: {status_str} (Survival: {survival_prob*100:.2f}%, Max DD: {max_dd*100:.2f}%)")
                
            if records:
                self.repo.con.executemany("""
                    INSERT OR REPLACE INTO black_swan_simulations 
                    (date, scenario_name, simulated_drawdown_pct, survival_probability, portfolio_resilient)
                    VALUES (?, ?, ?, ?, ?)
                """, records)
                
        except Exception as e:
            logger.error(f"Black Swan simulation failed: {e}")

    def _simulate_merton_jump_diffusion(self, s0, mu, sigma, lambda_j, mu_j, sigma_j, num_paths, days):
        """
        Phase 13.3.2: Heavily vectorized numpy Merton Jump-Diffusion.
        """
        dt = 1.0 # Daily steps
        
        # 1. Brownian Motion Component
        Z = np.random.standard_normal((num_paths, days))
        diffusion_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
        
        # 2. Jump Component (Poisson Process)
        # N ~ Poisson(lambda * dt)
        N = np.random.poisson(lambda_j * dt, (num_paths, days))
        
        # Jumps sizes are log-normal: log(1+k) ~ N(mu_j, sigma_j^2)
        # To avoid loops, we simulate the maximum expected jumps per day. Usually 0 or 1.
        # We can approximate the daily jump sum if multiple jumps occur, though rare.
        # Simplified vectorization: sum of N normal variables.
        # We use a conditional approach or just generate a massive array and sum.
        # For performance, we approximate: Jump Return ~ N(N*mu_j, N*sigma_j^2)
        # This holds roughly by properties of normals if N is known.
        
        jump_returns = np.zeros_like(diffusion_returns)
        mask_jumps = N > 0
        if np.any(mask_jumps):
            # For each path/day that has jumps, sample from normal
            # N is the number of jumps. 
            jump_returns[mask_jumps] = np.random.normal(
                N[mask_jumps] * mu_j, 
                np.sqrt(N[mask_jumps]) * sigma_j
            )
            
        # 3. Total Daily Log Returns
        total_log_returns = diffusion_returns + jump_returns
        
        # 4. Price Paths
        # S_t = S_0 * exp(cumsum(log_returns))
        cumulative_log_returns = np.cumsum(total_log_returns, axis=1)
        price_paths = s0 * np.exp(cumulative_log_returns)
        
        # Add day 0
        price_paths = np.hstack((np.full((num_paths, 1), s0), price_paths))
        
        # 5. Analysis
        # Portfolio drops by more than 20%
        min_prices = np.min(price_paths, axis=1)
        drawdowns = (s0 - min_prices) / s0
        
        # Paths that did NOT drop by more than 20%
        survived_paths = np.sum(drawdowns <= 0.20)
        survival_prob = survived_paths / num_paths
        
        # 99th percentile worst drawdown
        worst_dd = np.percentile(drawdowns, 99)
        
        return {
            "survival_probability": float(survival_prob),
            "worst_drawdown": float(worst_dd)
        }
