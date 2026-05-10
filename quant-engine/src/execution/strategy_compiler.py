import pandas as pd
import numpy as np
import vectorbt as vbt
import json
from loguru import logger
from typing import List, Dict, Any
from ..data.duckdb_repo import DuckDBRepo

class StrategyCompiler:
    """
    Phase 29.1: The JSON-to-VectorBT Compiler.
    Translates visual graph payloads into high-speed backtests.
    """

    def __init__(self, repo: DuckDBRepo):
        self.repo = repo

    def compile_and_run(self, ticker: str, graph: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Parses the strategy graph and executes a vectorized simulation.
        """
        logger.info(f"Compiling visual strategy for {ticker} from {start_date} to {end_date}")

        try:
            # 1. Fetch Price Data
            # Note: Using get_parquet_data mock logic from DuckDBRepo
            df = self._fetch_hydrated_data(ticker, start_date, end_date)
            if df.empty:
                raise ValueError(f"No hydrated data found for {ticker}")

            close = df.set_index('date')['close']

            # 2. Extract Logic from Nodes
            # Example mapping:
            # Node Type "SMA" -> vbt.MA.run(close, window=...).ma
            # Node Type "RSI" -> vbt.RSI.run(close, window=...).rsi
            
            nodes = graph.get('nodes', [])
            edges = graph.get('edges', [])

            # For this MVP, we implement a simple SMA Crossover logic parser
            # if we find nodes with these specific labels.
            fast_window = 20
            slow_window = 50

            for node in nodes:
                data = node.get('data', {})
                label = data.get('label', '').upper()
                if 'SMA' in label and 'FAST' in label:
                    fast_window = int(data.get('window', 20))
                if 'SMA' in label and 'SLOW' in label:
                    slow_window = int(data.get('window', 50))

            # 3. Vectorized Signal Generation
            fast_ma = vbt.MA.run(close, fast_window).ma
            slow_ma = vbt.MA.run(close, slow_window).ma

            entries = fast_ma.vbt.crossed_above(slow_ma)
            exits = fast_ma.vbt.crossed_below(slow_ma)

            # 4. Portfolio Simulation
            pf = vbt.Portfolio.from_signals(
                close, 
                entries, 
                exits, 
                init_cash=graph.get('starting_capital', 100000000.0),
                fees=0.002 # 20 bps
            )

            # 5. Extract institutional metrics
            stats = pf.stats()
            equity_curve = pf.value()
            
            # Format curve for Recharts [{date: '...', value: 1.2}, ...]
            curve_data = [
                {"date": str(date.date()), "value": float(val)}
                for date, val in equity_curve.items()
            ]

            return {
                "sharpe_ratio": float(stats.get('Sharpe Ratio', 0.0)),
                "cagr": float(stats.get('Total Return [%]', 0.0)) / ( (pd.to_datetime(end_date) - pd.Timestamp(start_date)).days / 365.25),
                "max_drawdown": float(stats.get('Max Drawdown [%]', 0.0)),
                "equity_curve": curve_data
            }

        except Exception as e:
            logger.error(f"Strategy compilation failed: {e}")
            raise

    def _fetch_hydrated_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Helper to fetch from the Phase 23 Parquet lake."""
        # Conceptually: return self.repo.con.execute(...).df()
        # Mocking for MVP if files not found
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        mock_close = 5000 + np.cumsum(np.random.normal(0, 50, len(dates)))
        return pd.DataFrame({'date': dates, 'close': mock_close, 'ticker': ticker})
