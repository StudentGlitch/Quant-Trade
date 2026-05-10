import numpy as np
from scipy.stats import norm
from loguru import logger

class OptionsPricer:
    """
    Phase 20.1: Black-Scholes-Merton Options Pricing & Greeks.
    Includes Newton-Raphson root finding for Implied Volatility.
    """

    @staticmethod
    def black_scholes(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'CALL') -> float:
        """
        Calculate Black-Scholes price for European options.
        S: Underlying Price, K: Strike, T: Time to Maturity (Years), r: Risk-free rate, sigma: Volatility.
        """
        if T <= 0:
            return max(0.0, S - K) if option_type == 'CALL' else max(0.0, K - S)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type.upper() == 'CALL':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
        return float(price)

    @staticmethod
    def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'CALL') -> dict:
        """Calculate Delta, Gamma, Theta, Vega, Rho."""
        if T <= 0:
            return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type.upper() == 'CALL':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
            
        # Gamma (Same for Call and Put)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Vega (Same for Call and Put)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100 # Per 1% change
        
        # Theta
        if option_type.upper() == 'CALL':
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
            
        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta)
        }

    @staticmethod
    def implied_volatility(market_price: float, S: float, K: float, T: float, r: float, option_type: str = 'CALL') -> float:
        """Find IV using Newton-Raphson method (PRD 7.2)."""
        sigma = 0.3  # Initial guess
        precision = 1.0e-5
        max_iterations = 100
        
        for i in range(max_iterations):
            price = OptionsPricer.black_scholes(S, K, T, r, sigma, option_type)
            # Vega is the partial derivative of price with respect to sigma
            d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
            vega = S * norm.pdf(d1) * np.sqrt(T)
            
            diff = market_price - price
            
            if abs(diff) < precision:
                return float(sigma)
            
            if vega == 0:
                break
                
            sigma = sigma + diff / vega # Newton step
            
            # Constraints
            if sigma <= 0:
                sigma = 0.001
            elif sigma > 5.0:
                sigma = 5.0
                
        return None # Failed to converge
