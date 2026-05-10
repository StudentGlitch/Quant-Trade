import pytest
import numpy as np
from src.derivatives.pricer import OptionsPricer

def test_black_scholes_standard_case():
    """
    Test against known textbook example:
    S=100, K=100, T=1, r=0.05, sigma=0.2
    Expected Call Price: ~10.4506
    Expected Call Delta: ~0.6368
    """
    S, K, T, r, sigma = 100, 100, 1, 0.05, 0.2
    
    price = OptionsPricer.black_scholes(S, K, T, r, sigma, 'CALL')
    greeks = OptionsPricer.calculate_greeks(S, K, T, r, sigma, 'CALL')
    
    assert abs(price - 10.4506) < 1e-4
    assert abs(greeks['delta'] - 0.6368) < 1e-4

def test_implied_volatility_convergence():
    """Ensure Newton-Raphson can work backward to the original sigma."""
    S, K, T, r, target_sigma = 100, 100, 1, 0.05, 0.25
    market_price = OptionsPricer.black_scholes(S, K, T, r, target_sigma, 'CALL')
    
    calc_iv = OptionsPricer.implied_volatility(market_price, S, K, T, r, 'CALL')
    
    assert abs(calc_iv - target_sigma) < 1e-4

def test_put_call_parity_check():
    """Verify Put price logic via a simple call-put comparison."""
    S, K, T, r, sigma = 100, 105, 0.5, 0.03, 0.2
    call_p = OptionsPricer.black_scholes(S, K, T, r, sigma, 'CALL')
    put_p = OptionsPricer.black_scholes(S, K, T, r, sigma, 'PUT')
    
    # C - P = S - K*e^(-rT)
    lhs = call_p - put_p
    rhs = S - K * np.exp(-r * T)
    
    assert abs(lhs - rhs) < 1e-4
