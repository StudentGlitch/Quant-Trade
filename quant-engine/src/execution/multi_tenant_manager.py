import pandas as pd
from loguru import logger
import numpy as np
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo

class MultiTenantManager:
    """
    Phase 11.2: Multi-Strategy Engine & Sub-Ledgers.
    Calculates daily PnL independently for each user based on their specific strategy allocation.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def process_sub_ledgers(self, date: str):
        """Loop through all users and update their individual paper current_equity."""
        logger.info(f"Multi-Tenant Manager: Processing sub-ledgers for {date}...")
        
        try:
            # 1. Calculate daily returns for each strategy
            # In a real system, we'd calculate this based on the exact price changes 
            # of the specific portfolio_targets_multi allocations from yesterday to today.
            # For this MVP, we approximate using the master ledger's return scaled by Beta.
            
            master_pnl = self.repo.execute("SELECT * FROM daily_pnl_ledger ORDER BY date DESC LIMIT 2").df()
            if len(master_pnl) < 2:
                logger.warning("Insufficient master ledger history to compute sub-ledgers.")
                return
                
            today_equity = master_pnl['total_equity'].iloc[0]
            yest_equity = master_pnl['total_equity'].iloc[1]
            master_return = (today_equity - yest_equity) / yest_equity if yest_equity > 0 else 0.0
            
            # Simulated Strategy Returns
            strategy_returns = {
                'SWARM_MARKET_NEUTRAL': master_return,
                'SWARM_DEFENSIVE': master_return * 0.5, # Less volatile
                'SWARM_AGGRESSIVE': master_return * 1.5  # More volatile
            }
            
            # 2. Get all active user sub-ledger allocations for the PREVIOUS day
            # (or the most recent day they had an allocation)
            ledgers = self.repo.execute("""
                SELECT user_id, strategy_name, current_equity
                FROM user_sub_ledgers
                WHERE date = (SELECT MAX(date) FROM user_sub_ledgers)
            """).df()
            
            if ledgers.empty:
                logger.info("No active user sub-ledgers found.")
                return
                
            # 3. Apply Returns and Upsert
            records = []
            for _, row in ledgers.iterrows():
                user_id = row['user_id']
                strategy = row['strategy_name']
                start_equity = row['current_equity']
                
                daily_ret = strategy_returns.get(strategy, 0.0)
                daily_pnl = start_equity * daily_ret
                new_equity = start_equity + daily_pnl
                
                records.append((date, user_id, strategy, start_equity, new_equity, daily_pnl))
                
            if records:
                self.repo.con.executemany("""
                    INSERT OR REPLACE INTO user_sub_ledgers (date, user_id, strategy_name, allocated_capital, current_equity, daily_pnl)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, records)
                logger.success(f"Successfully processed {len(records)} user sub-ledgers.")
                
        except Exception as e:
            logger.error(f"Failed to process sub-ledgers: {e}")

    def get_user_dashboard_data(self, user_id: str) -> dict:
        """Fetch isolated sub-ledger data for the Investor Portal API."""
        try:
            df = self.repo.execute("""
                SELECT date, strategy_name, current_equity, daily_pnl 
                FROM user_sub_ledgers 
                WHERE user_id = ? 
                ORDER BY date
            """, [user_id]).df()
            
            if df.empty:
                # Initialize new user with mock $10k paper account across a strategy
                self.repo.execute("""
                    INSERT INTO user_sub_ledgers (date, user_id, strategy_name, allocated_capital, current_equity, daily_pnl)
                    VALUES (CURRENT_DATE, ?, 'SWARM_MARKET_NEUTRAL', 10000.0, 10000.0, 0.0)
                """, [user_id])
                
                return {
                    "total_equity": 10000.0,
                    "allocations": [{"strategy": "SWARM_MARKET_NEUTRAL", "value": 10000.0}],
                    "history": [{"date": pd.Timestamp.now().strftime('%Y-%m-%d'), "equity": 10000.0}]
                }
                
            latest = df[df['date'] == df['date'].max()]
            total_equity = latest['current_equity'].sum()
            
            allocs = []
            for _, row in latest.iterrows():
                allocs.append({"strategy": row['strategy_name'], "value": float(row['current_equity'])})
                
            history = []
            for date, group in df.groupby('date'):
                history.append({"date": str(date), "equity": float(group['current_equity'].sum())})
                
            return {
                "total_equity": float(total_equity),
                "allocations": allocs,
                "history": history
            }
        except Exception as e:
            logger.error(f"Error fetching user dashboard: {e}")
            return {"total_equity": 0.0, "allocations": [], "history": []}
