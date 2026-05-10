import pandas as pd
import numpy as np
from loguru import logger
from .ledger_manager import LedgerManager
from ..data.duckdb_repo import DuckDBRepo

class OrderRouter:
    """
    Phase 4.2: Order Execution Simulator.
    Calculates Delta & Executes Paper Trades with Slippage (PRD 7.1).
    """
    
    def __init__(self, repo: DuckDBRepo, ledger: LedgerManager):
        self.repo = repo
        self.ledger = ledger

    def execute_rebalance(self, date):
        """Transition from Target Weights to Executed Holdings."""
        logger.info(f"Starting simulated execution rebalance for {date}...")
        
        # 1. Read ideal weights
        targets = self.repo.execute(f"SELECT ticker, target_weight_pct FROM portfolio_targets WHERE date = '{date}'").df()
        if targets.empty:
            logger.warning("No portfolio targets found for rebalance.")
            return

        # 2. Read current state
        current_cash, current_positions = self.ledger.get_current_state()
        
        # Calculate Total Portfolio Value (TPV)
        # To get TPV, we need current prices
        tickers = targets['ticker'].tolist()
        if not current_positions.empty:
            tickers = list(set(tickers + current_positions['ticker'].tolist()))
            
        prices = self._get_latest_prices(tickers, date)
        
        position_value = 0.0
        if not current_positions.empty:
            for _, pos in current_positions.iterrows():
                price = prices.get(pos['ticker'], 0.0)
                position_value += pos['shares_held'] * price
                
        tpv = current_cash + position_value
        logger.info(f"Total Portfolio Value (TPV): {tpv:,.2f} IDR")

        # 3. Calculate Deltas and Execute
        # Map targets to target value
        targets['target_value'] = targets['target_weight_pct'] * tpv
        
        # Track trades
        trades = []
        
        # 3.1 Handle Sells (and Reductions) first to free up cash
        all_tickers = set(targets['ticker'].tolist()) | set(current_positions['ticker'].tolist() if not current_positions.empty else [])
        
        for ticker in all_tickers:
            target_val = targets[targets['ticker'] == ticker]['target_value'].values[0] if ticker in targets['ticker'].values else 0.0
            current_pos = current_positions[current_positions['ticker'] == ticker]
            current_shares = current_pos['shares_held'].values[0] if not current_pos.empty else 0
            current_val = current_shares * prices.get(ticker, 0.0)
            
            delta_val = target_val - current_val
            price = prices.get(ticker, 0.0)
            
            if price == 0: continue
            
            # Q_order (number of shares)
            q_order = int(delta_val / price)
            
            # Round to nearest 100 (Lot size)
            q_order = (q_order // 100) * 100
            
            if q_order == 0: continue
            
            # Execute Trade
            exec_price, cost = self._simulate_trade(ticker, q_order, price)
            
            # Update Cash
            current_cash -= (q_order * exec_price)
            
            # Update Inventory
            self._update_inventory(ticker, q_order, exec_price, date)
            
            trades.append({
                "ticker": ticker,
                "q_order": q_order,
                "exec_price": exec_price,
                "cost": cost
            })
            
        # 4. Final Ledger Update
        # Calculate final equity and PnL
        final_pos_val = 0.0
        _, updated_positions = self.ledger.get_current_state()
        for _, pos in updated_positions.iterrows():
            final_pos_val += pos['shares_held'] * prices.get(pos['ticker'], 0.0)
            
        final_tpv = current_cash + final_pos_val
        
        # Mock unrealized/realized for now
        # In a full system, you'd track cost basis
        self.ledger.update_pnl(date, final_tpv, current_cash, 0.0, 0.0, 7000.0)
        
        logger.success(f"Rebalance complete. Executed {len(trades)} trades. Final TPV: {final_tpv:,.2f}")

    def _get_latest_prices(self, tickers, date):
        """Fetch EOD prices for a list of tickers."""
        # This would normally query the Parquet/DuckDB
        prices = {}
        for ticker in tickers:
            try:
                # Optimized subquery
                res = self.repo.execute(f"""
                    SELECT close FROM read_parquet('storage/parquet_data/ticker=*/data.parquet', hive_partitioning=1) 
                    WHERE ticker = '{ticker}' AND date <= '{date}' ORDER BY date DESC LIMIT 1
                """).fetchone()
                if res:
                    prices[ticker] = res[0]
            except:
                pass
        return prices

    def _simulate_trade(self, ticker, q_order, p_close):
        """Apply Transaction Cost & Slippage math (PRD 7.1)."""
        # Mock ADV for slippage
        v_adv = 10_000_000 
        
        s_impact = 0.10 * (abs(q_order) / v_adv)**2
        
        if q_order > 0: # BUY
            # Broker Fee + PPN + Levy = approx 0.15%
            p_exec = p_close * (1 + 0.0015 + s_impact)
        else: # SELL
            # Includes extra 0.10% Final Income Tax
            p_exec = p_close * (1 - 0.0025 - s_impact)
            
        cost = abs(q_order * (p_exec - p_close))
        return p_exec, cost

    def _update_inventory(self, ticker, q_order, p_exec, date):
        """Update position_inventory table."""
        current = self.repo.execute(f"SELECT shares_held, average_entry_price FROM position_inventory WHERE ticker = '{ticker}'").fetchone()
        
        if not current:
            if q_order > 0:
                self.repo.execute("""
                    INSERT INTO position_inventory (ticker, shares_held, average_entry_price, last_updated)
                    VALUES (?, ?, ?, ?)
                """, [ticker, q_order, p_exec, date])
        else:
            old_shares, old_avg = current
            new_shares = old_shares + q_order
            
            if new_shares > 0:
                if q_order > 0:
                    # New Average Cost
                    new_avg = ((old_shares * old_avg) + (q_order * p_exec)) / new_shares
                else:
                    new_avg = old_avg # Average cost doesn't change on partial sell
                    
                self.repo.execute("""
                    UPDATE position_inventory 
                    SET shares_held = ?, average_entry_price = ?, last_updated = ?
                    WHERE ticker = ?
                """, [new_shares, new_avg, date, ticker])
            else:
                self.repo.execute("DELETE FROM position_inventory WHERE ticker = ?", [ticker])
