import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces
from typing import Optional

class MarketMicrostructureEnv(gym.Env):
    """
    Phase 17.1: Custom Gymnasium environment for DRL execution.
    Simulates intraday market impact and implementation shortfall.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, total_quantity: int, T: int = 12, arrival_price: float = 100.0, sigma: float = 0.01):
        super(MarketMicrostructureEnv, self).__init__()
        
        self.X = total_quantity  # Parent quantity
        self.T = T              # Number of time steps (e.g., 12 half-hours in a day)
        self.P0 = arrival_price
        self.sigma = sigma      # Daily volatility
        
        # Action space: [0, 1] percentage of remaining order to execute
        self.action_space = spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        
        # Observation space: [Time Remaining, Q Remaining, Current Price, Volatility]
        self.observation_space = spaces.Box(
            low=0, high=np.inf, shape=(4,), dtype=np.float32
        )

        self.reset()

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)
        
        self.time_step = 0
        self.q_remaining = self.X
        self.current_price = self.P0
        self.total_is = 0.0
        
        # Simulate an intraday path using Brownian Bridge
        self.prices = self._simulate_brownian_bridge()
        
        obs = self._get_obs()
        return obs, {}

    def step(self, action):
        # 1. Determine quantity to execute
        q_to_execute = int(self.q_remaining * action[0])
        
        # Force fill if last step
        if self.time_step == self.T - 1:
            q_to_execute = self.q_remaining
            
        # 2. Calculate Market Impact (Naive Quadratic Model for Simulation)
        # S_impact = alpha * (q / V)**beta
        # Using a simplified linear impact for the env logic
        temporary_impact = 0.0001 * (q_to_execute / self.X) * self.current_price
        executed_price = self.current_price + temporary_impact
        
        # 3. Calculate Reward (Implementation Shortfall)
        # IS = sum(executed_price - arrival_price) * q
        step_is = (executed_price - self.P0) * q_to_execute
        self.total_is += step_is
        
        # Negative reward proportional to IS
        reward = -step_is / (self.X * self.P0)
        
        # 4. Update State
        self.q_remaining -= q_to_execute
        self.time_step += 1
        
        if self.time_step < self.T:
            self.current_price = self.prices[self.time_step]
        
        # 5. Penalties
        terminated = self.time_step >= self.T
        if terminated and self.q_remaining > 0:
            # Massive penalty for failing to fill (PRD 7.1)
            reward -= 10.0 * (self.q_remaining / self.X)**2
            
        truncated = False
        obs = self._get_obs()
        
        return obs, reward, terminated, truncated, {
            "executed_quantity": q_to_execute,
            "executed_price": executed_price,
            "is_bps": (step_is / (self.X * self.P0)) * 10000
        }

    def _get_obs(self):
        return np.array([
            float(self.T - self.time_step),
            float(self.q_remaining),
            float(self.current_price),
            float(self.sigma)
        ], dtype=np.float32)

    def _simulate_brownian_bridge(self):
        """Intraday Brownian Bridge Simulation (PRD 7.2)."""
        # Constrain P_end close to P_start for a standard day
        p_start = self.P0
        p_end = self.P0 * (1 + np.random.normal(0, self.sigma))
        
        times = np.linspace(0, 1, self.T)
        standard_bm = np.cumsum(np.random.normal(0, self.sigma / np.sqrt(self.T), self.T))
        
        # Bridge formula
        bridge = p_start + times * (p_end - p_start) + \
                 (standard_bm - times * standard_bm[-1])
        
        return bridge
