import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict
from ..data.duckdb_repo import DuckDBRepo

class RiskParityAllocator:
    """
    Phase 3.1: Portfolio Allocation Engine.
    Implements Inverse Volatility Risk Parity Weighting and Macro Cash Drag.
    Adapted from APIClientTemplate for internal processing.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def fetch_candidates(self) -> pd.DataFrame:
        """Fetch the Top 15 eligible candidates using dynamic SQL (PRD 6.2)."""
        logger.info("Fetching Top 15 portfolio candidates...")
        query = """
            WITH RecentSignals AS (
                SELECT
                    m.ticker, m.company_name, m.sector,
                    p.close AS close_price,
                    p.volatility_20d AS volatility_30d, -- Using existing 20d volatility for 30d proxy as per schema
                    t.final_direction AS blended_signal,
                    t.llm_signal
                FROM
                    idx_metadata m
                JOIN
                    read_parquet('storage/parquet_data/ticker=*/data.parquet', hive_partitioning=1) p
                ON m.ticker = p.ticker
                JOIN
                    paper_trades t ON m.ticker = t.ticker
                WHERE
                    p.date = (SELECT MAX(date) FROM read_parquet('storage/parquet_data/ticker=*/data.parquet'))
                    AND t.final_direction > 0.65 -- Strong Buy Threshold
                    AND m.avg_daily_volume > 5000000 -- Liquidity check for portfolio inclusion
            )
            SELECT * FROM RecentSignals ORDER BY blended_signal DESC LIMIT 15;
        """
        try:
            df = self.repo.execute(query).df()
            return df
        except Exception as e:
            logger.error(f"Error fetching portfolio candidates: {e}")
            return pd.DataFrame()

    def calculate_allocation(self, df: pd.DataFrame, macro_df: pd.DataFrame) -> Dict[str, float]:
        """Apply Inverse Volatility math (7.1) and Macro Cash Drag (7.2)."""
        if df.empty or macro_df.empty:
            logger.warning("Missing data for allocation calculation.")
            return {}

        logger.info("Calculating Risk Parity allocation...")
        
        # 7.2 The Macro "Risk Sentinel" Cash Drag
        # Assuming R_macro is calculated based on VIX for this implementation
        # A simple normalization of VIX (0.0 = Safe (VIX<=15), 1.0 = Extreme Crisis (VIX>=40))
        latest_vix = macro_df.iloc[-1]['vix_close']
        r_macro = max(0.0, min(1.0, (latest_vix - 15) / (40 - 15)))
        
        cash_pct = max(0.0, min(0.50, r_macro * 0.50))
        logger.info(f"Macro Risk Score (R_macro): {r_macro:.2f}, Cash Drag: {cash_pct:.2f}")

        # 7.1 Inverse Volatility Risk Parity Weighting
        investable_pct = 1.0 - cash_pct
        
        # Phase 6.2: CIO Overseer Integration
        # Check for Kill Switch override from the risk ledger
        try:
            override_active = self.repo.execute("SELECT cio_override_active FROM risk_metrics_ledger ORDER BY date DESC LIMIT 1").fetchone()
            if override_active and override_active[0]:
                logger.critical("CIO KILL SWITCH DETECTED. Liquidating all positions to 100% Cash.")
                cash_pct = 1.0
                investable_pct = 0.0
        except Exception as e:
            logger.error(f"Failed to check CIO override: {e}")

        # Calculate unnormalized weights: w'_i = 1 / sigma_i
        # Prevent division by zero
        df['unnormalized_weight'] = 1 / df['volatility_30d'].replace(0, np.nan).fillna(0.0001)
        
        total_unnormalized_weight = df['unnormalized_weight'].sum()
        
        allocations = {}
        allocations['SWARM_MARKET_NEUTRAL'] = {'CASH': cash_pct}
        allocations['SWARM_DEFENSIVE'] = {'CASH': 0.5 + (cash_pct * 0.5)}
        allocations['SWARM_AGGRESSIVE'] = {'CASH': 0.0} # Aggressive eliminates cash drag
        
        if total_unnormalized_weight > 0:
            df['target_weight_pct'] = (df['unnormalized_weight'] / total_unnormalized_weight) * investable_pct
            for _, row in df.iterrows():
                ticker = row['ticker']
                base_w = row['target_weight_pct']
                
                # Normal (Market Neutral)
                allocations['SWARM_MARKET_NEUTRAL'][ticker] = base_w
                
                # Defensive (Beta = 0.5)
                allocations['SWARM_DEFENSIVE'][ticker] = base_w * 0.5
                
        # Aggressive logic: Concentrate into top 5 instead of 15
        if total_unnormalized_weight > 0:
            top_5 = df.nlargest(5, 'target_weight_pct')
            top_5_unnorm = top_5['unnormalized_weight'].sum()
            if top_5_unnorm > 0:
                for _, row in top_5.iterrows():
                    allocations['SWARM_AGGRESSIVE'][row['ticker']] = (row['unnormalized_weight'] / top_5_unnorm) * 1.0 # 100% equity
                
        return allocations

    def store_data(self, multi_allocations: Dict[str, Dict[str, float]], df: pd.DataFrame) -> None:
        """Upsert allocation data into DuckDB for multiple strategies."""
        if not multi_allocations:
            return
            
        logger.info("Storing multi-strategy portfolio targets...")
        
        # We need a new table schema or add strategy_name to portfolio_targets
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_targets_multi (
                date DATE,
                strategy_name VARCHAR,
                ticker VARCHAR,
                target_weight_pct DOUBLE,
                llm_conviction DOUBLE,
                volatility_30d DOUBLE,
                PRIMARY KEY (date, strategy_name, ticker)
            );
        """)
        
        current_date = pd.Timestamp.now().date()
        records = []
        
        for strategy, allocations in multi_allocations.items():
            for ticker, weight in allocations.items():
                if ticker == 'CASH':
                    # We might want to store cash explicitly
                    records.append((current_date, strategy, 'CASH', weight, 0.0, 0.0))
                    continue
                    
                row = df[df['ticker'] == ticker].iloc[0]
                records.append((
                    current_date, 
                    strategy,
                    ticker, 
                    weight, 
                    row.get('llm_signal', 0.0), 
                    row.get('volatility_30d', 0.0)
                ))
            
        if records:
            query = "INSERT OR REPLACE INTO portfolio_targets_multi VALUES (?, ?, ?, ?, ?, ?)"
            try:
                self.repo.con.executemany(query, records)
                logger.success(f"Stored {len(records)} multi-strategy targets.")
                
                # Backwards compatibility for Phase 10 Live Execution which reads from portfolio_targets
                # We'll map the master SWARM_MARKET_NEUTRAL to the old table
                master_records = [r for r in records if r[1] == 'SWARM_MARKET_NEUTRAL' and r[2] != 'CASH']
                if master_records:
                    self.repo.execute("""
                        CREATE TABLE IF NOT EXISTS portfolio_targets (
                            date DATE, ticker VARCHAR, target_weight_pct DOUBLE, llm_conviction DOUBLE, volatility_30d DOUBLE, PRIMARY KEY (date, ticker)
                        );
                    """)
                    bc_records = [(r[0], r[2], r[3], r[4], r[5]) for r in master_records]
                    self.repo.con.executemany("INSERT OR REPLACE INTO portfolio_targets VALUES (?, ?, ?, ?, ?)", bc_records)
                    
            except Exception as e:
                logger.error(f"Failed to store portfolio targets: {e}")
                
        # Also store cash component if needed, or handle separately

    def run(self):
        """Execute the allocation process."""
        candidates_df = self.fetch_candidates()
        
        try:
            macro_df = self.repo.execute("SELECT * FROM macro_data ORDER BY date").df()
        except Exception as e:
            logger.error(f"Failed to fetch macro data: {e}")
            macro_df = pd.DataFrame()
            
        allocations = self.calculate_allocation(candidates_df, macro_df)
        self.store_data(allocations, candidates_df)
        return allocations
