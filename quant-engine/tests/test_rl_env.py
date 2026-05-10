import pytest
import numpy as np
from src.execution.rl_environment import MarketMicrostructureEnv

def test_rl_env_reset():
    env = MarketMicrostructureEnv(total_quantity=1000, T=10)
    obs, info = env.reset()
    
    assert obs.shape == (4,)
    assert obs[0] == 10.0 # T remaining
    assert obs[1] == 1000.0 # Q remaining
    assert len(env.prices) == 10

def test_rl_env_step_full_fill():
    env = MarketMicrostructureEnv(total_quantity=1000, T=2)
    env.reset()
    
    # Step 1: Execute 50%
    obs, reward, terminated, truncated, info = env.step(np.array([0.5]))
    assert info['executed_quantity'] == 500
    assert not terminated
    
    # Step 2: Last step should force fill remaining
    obs, reward, terminated, truncated, info = env.step(np.array([0.1]))
    assert info['executed_quantity'] == 500
    assert env.q_remaining == 0
    assert terminated

def test_brownian_bridge_math():
    env = MarketMicrostructureEnv(total_quantity=100, T=100, arrival_price=100.0, sigma=0.01)
    prices = env._simulate_brownian_bridge()
    
    assert len(prices) == 100
    assert prices[0] == 100.0
    # Last price should be within a reasonable range of arrival
    assert 90.0 < prices[-1] < 110.0
