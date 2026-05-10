import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime
from ..data.duckdb_repo import DuckDBRepo

class LedgerManager:
    """
    Phase 4.1: Ledger Management.
    Manages DB Cash & Position Inventory.
    """
    
    def __init__(self, repo: DuckDBRepo):
        self.repo = repo
        self._initialize_tables()

    def _initialize_tables(self):
        """Ensure position_inventory and daily_pnl_ledger tables exist (PRD 6.1)."""
        logger.info("Initializing Ledger tables...")
        
        # Position Inventory
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS position_inventory (
                ticker VARCHAR PRIMARY KEY,
                shares_held BIGINT DEFAULT 0,
                average_entry_price DOUBLE,
                last_updated DATE
            );
        """)
        
        # Daily PnL Ledger
        self.repo.execute("""
            CREATE TABLE IF NOT EXISTS daily_pnl_ledger (
                date DATE PRIMARY KEY,
                total_equity DOUBLE, -- Cash + (Shares * Close)
                cash_balance DOUBLE,
                realized_pnl DOUBLE,
                unrealized_pnl DOUBLE,
                benchmark_value DOUBLE -- IHSG close price
            );
        """)
        
        # Initialize starting cash if empty (PRD 8.1.3)
        check_empty = self.repo.execute("SELECT count(*) FROM daily_pnl_ledger").fetchone()[0]
        if check_empty == 0:
            starting_cash = 100_000_000.0
            logger.info(f"Initializing ledger with {starting_cash:,} IDR starting cash.")
            # We use a date in the past or current date
            initial_date = '2026-01-01' # Placeholder start date
            self.repo.execute("""
                INSERT INTO daily_pnl_ledger (date, total_equity, cash_balance, realized_pnl, unrealized_pnl, benchmark_value)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [initial_date, starting_cash, starting_cash, 0.0, 0.0, 6600.0]) # Mock benchmark start

    def get_current_state(self):
        """Fetch current cash balance and position inventory."""
        cash = self.repo.execute("SELECT cash_balance FROM daily_pnl_ledger ORDER BY date DESC LIMIT 1").fetchone()[0]
        positions = self.repo.execute("SELECT * FROM position_inventory WHERE shares_held > 0").df()
        return cash, positions

    def update_pnl(self, date, total_equity, cash_balance, realized, unrealized, benchmark):
        """Record daily PnL snapshot."""
        self.repo.execute("""
            INSERT OR REPLACE INTO daily_pnl_ledger (date, total_equity, cash_balance, realized_pnl, unrealized_pnl, benchmark_value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [date, total_equity, cash_balance, realized, unrealized, benchmark])
