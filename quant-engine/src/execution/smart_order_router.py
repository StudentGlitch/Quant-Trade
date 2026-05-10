import uuid
import numpy as np
from stable_baselines3 import PPO
from .rl_environment import MarketMicrostructureEnv
from ..data.duckdb_repo import DuckDBRepo
from loguru import logger
from datetime import datetime

class SmartOrderRouter:
    """Phase 17.3: Integrates DRL agent into OMS for optimal order slicing."""

    def __init__(self, repo: DuckDBRepo, model_path: str = "storage/artifacts/models/drl_execution.zip"):
        self.repo = repo
        try:
            self.model = PPO.load(model_path)
            logger.info("DRL Execution Model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load DRL model: {e}. Falling back to naive TWAP.")
            self.model = None

    def execute_parent_order(self, ticker: str, total_quantity: int, arrival_price: float, sigma: float = 0.01):
        """Slices a parent order into children using DRL policy."""
        parent_id = str(uuid.uuid4())
        logger.info(f"Execution started for {ticker}: {total_quantity} shares @ {arrival_price}")

        # 1. Initialize Simulation Environment for this order
        env = MarketMicrostructureEnv(total_quantity=total_quantity, arrival_price=arrival_price, sigma=sigma)
        
        # 2. Record Parent Order
        self.repo.execute("""
            INSERT INTO parent_orders (parent_id, ticker, order_type, total_quantity, start_time, status)
            VALUES (?, ?, 'MARKET_SLICE', ?, ?, 'EXECUTING')
        """, [parent_id, ticker, total_quantity, datetime.now()])

        obs, _ = env.reset()
        done = False
        child_records = []
        total_executed_price = 0
        total_executed_qty = 0

        # 3. Step through the day using the DRL Policy
        while not done:
            if self.model:
                action, _ = self.model.predict(obs, deterministic=True)
            else:
                # Naive TWAP fallback
                action = [1.0 / env.T]

            obs, reward, terminated, truncated, info = env.step(action)
            
            child_id = str(uuid.uuid4())
            q_exec = info['executed_quantity']
            p_exec = info['executed_price']
            
            if q_exec > 0:
                child_records.append((
                    child_id, parent_id, datetime.now(), q_exec, p_exec, info['is_bps']
                ))
                total_executed_price += p_exec * q_exec
                total_executed_qty += q_exec

            done = terminated or truncated

        # 4. Finalize Execution Analytics
        avg_price = total_executed_price / total_executed_qty if total_executed_qty > 0 else arrival_price
        
        # Calculate savings compared to naive model (quadratic slippage in one sweep)
        naive_impact = 0.005 * arrival_price # 50 bps mock
        naive_avg_price = arrival_price + naive_impact
        savings_bps = (naive_avg_price - avg_price) / arrival_price * 10000

        self.repo.execute("""
            UPDATE parent_orders 
            SET end_time = ?, actual_average_price = ?, drl_slippage_savings = ?, status = 'FILLED'
            WHERE parent_id = ?
        """, [datetime.now(), avg_price, savings_bps, parent_id])

        # 5. Bulk Insert Child Orders
        if child_records:
            self.repo.con.executemany("""
                INSERT INTO child_orders (child_id, parent_id, execution_time, executed_quantity, executed_price, market_impact_incurred)
                VALUES (?, ?, ?, ?, ?, ?)
            """, child_records)

        logger.success(f"Parent Order {parent_id} filled. Avg Price: {avg_price:.2f}. Savings: {savings_bps:.1f} bps")
        return parent_id
