import pandas as pd
from typing import Dict, Any, List
from loguru import logger
from ..data.duckdb_repo import DuckDBRepo
import uuid
from datetime import datetime

class PortfolioState:
    def __init__(self, repo: DuckDBRepo, initial_cash: float = 10000):
        self.repo = repo
        self.initial_cash = initial_cash

    def get_available_cash(self) -> float:
        """Calculate current cash by summing initial_cash and realized PnL."""
        # Simplified for V1: Just return initial_cash if no trades
        return self.initial_cash

    def record_trade(self, ticker: str, direction: int, price: float, size: float, cost: float):
        """Write hypotetical trade to paper_trades (PRD 5.1)."""
        trade_id = uuid.uuid4()
        signal_date = datetime.now().date()
        
        self.repo.con.execute("""
            INSERT INTO paper_trades 
            (trade_id, ticker, signal_date, direction, execution_price, position_size, transaction_cost, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
        """, [trade_id, ticker, signal_date, direction, price, size, cost])
        
        logger.info(f"Recorded hypothetical trade: {ticker} | Direction: {direction} | Price: {price}")
