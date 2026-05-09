import vectorbt as vbt
import pandas as pd
import numpy as np
import joblib
from loguru import logger
from typing import Dict, Any

class VectorBTEngine:
    def __init__(self, init_cash: float = 10000, fees: float = 0.0015, slippage: float = 0.0005):
        self.init_cash = init_cash
        self.fees = fees
        self.slippage = slippage

    def run(self, close_prices: pd.DataFrame, signals: pd.DataFrame) -> vbt.Portfolio:
        """Execute vectorized backtest (PRD 7 Phase 4.3)."""
        logger.info("Running VectorBT backtest...")
        
        # signals: 1 for long, -1 for short, 0 for neutral
        # vbt expects boolean entry/exit or discrete signals
        
        portfolio = vbt.Portfolio.from_signals(
            close_prices,
            entries=(signals == 1),
            exits=(signals == 0),
            short_entries=(signals == -1),
            short_exits=(signals == 0),
            init_cash=self.init_cash,
            fees=self.fees,
            slippage=self.slippage,
            freq='1D'
        )
        
        return portfolio

    def report(self, portfolio: vbt.Portfolio):
        """Output backtest tearsheet (PRD 7 Phase 4.4)."""
        stats = portfolio.stats()
        
        logger.info("\n--- BACKTEST TEARSHEET ---")
        logger.info(f"Total Return [%]: {stats['Total Return [%]']:.2f}%")
        logger.info(f"Annualized Sharpe Ratio: {stats['Sharpe Ratio']:.4f}")
        logger.info(f"Max Drawdown [%]: {stats['Max Drawdown [%]']:.2f}%")
        logger.info(f"Win Rate [%]: {stats['Win Rate [%]']:.2f}%")
        logger.info(f"Total Trades: {stats['Total Trades']}")
        logger.info(f"Profit Factor: {stats['Profit Factor']:.2f}")
        logger.info("--------------------------")
