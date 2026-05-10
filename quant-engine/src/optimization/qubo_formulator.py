import numpy as np
import pandas as pd
from loguru import logger
import dimod
from typing import List, Tuple

class QUBOFormulator:
    """
    Phase 32.2: Translates Portfolio Optimization into Quadratic Unconstrained Binary Optimization (QUBO).
    Discretizes continuous weights into binary spin states.
    """

    def __init__(self, num_assets: int, bits_per_weight: int = 4):
        self.num_assets = num_assets
        self.K = bits_per_weight # Precision
        # W_i = sum(2^k * x_i,k) * step_size
        # To sum to 1.0, max weight = 1.0. 
        # With 4 bits (0-15), step_size = 1/15 = 0.066
        self.step_size = 1.0 / (2**self.K - 1)

    def formulate_bqm(self, mu: np.ndarray, sigma: np.ndarray, gamma: float = 0.5) -> dimod.BinaryQuadraticModel:
        """
        Builds the Hamiltonian Energy function H.
        H = -sum(mu * W) + gamma * sum(sum(W * sigma * W))
        """
        logger.info(f"Formulating QUBO matrix for {self.num_assets} assets ({self.num_assets * self.K} binary variables)...")
        
        bqm = dimod.BinaryQuadraticModel(dimod.Vartype.BINARY)
        
        # 1. Linear Terms (Expected Returns)
        # -mu_i * W_i  =>  -mu_i * sum(2^k * step_size * x_i,k)
        for i in range(self.num_assets):
            for k in range(self.K):
                var_name = f"x_{i}_{k}"
                coefficient = -mu[i] * (2**k * self.step_size)
                bqm.add_variable(var_name, coefficient)

        # 2. Quadratic Terms (Risk/Covariance)
        # gamma * W_i * Sigma_ij * W_j
        # gamma * sum(2^k * step_size * x_i,k) * Sigma_ij * sum(2^m * step_size * x_j,m)
        for i in range(self.num_assets):
            for j in range(self.num_assets):
                cov_val = sigma[i, j]
                for k in range(self.K):
                    for m in range(self.K):
                        var_i = f"x_{i}_{k}"
                        var_j = f"x_{j}_{m}"
                        
                        # Quadratic coefficient
                        coeff = gamma * cov_val * (2**k * self.step_size) * (2**m * self.step_size)
                        
                        if var_i == var_j:
                            # Add to linear part of BQM (x^2 = x for binary)
                            bqm.add_variable(var_i, coeff)
                        else:
                            # Add to interaction part
                            bqm.add_interaction(var_i, var_j, coeff)

        # 3. Constraints: sum(W_i) = 1.0
        # penalty * (sum(W_i) - 1.0)^2
        # penalty * (sum_i sum_k (2^k * step_size * x_i,k) - 1.0)^2
        # For simplicity, we add this as a BQM constraint
        terms = []
        for i in range(self.num_assets):
            for k in range(self.K):
                terms.append((f"x_{i}_{k}", 2**k * self.step_size))
        
        bqm.add_linear_equality_constraint(
            terms,
            constant=-1.0,
            lagrangian_multiplier=10.0 # High penalty for violation
        )

        return bqm

    def decode_weights(self, sample: dict) -> np.ndarray:
        """Converts binary spin states back to floating point portfolio weights."""
        weights = np.zeros(self.num_assets)
        for i in range(self.num_assets):
            w_i = 0.0
            for k in range(self.K):
                val = sample.get(f"x_{i}_{k}", 0)
                w_i += (2**k * self.step_size) * val
            weights[i] = w_i
        
        # Normalize to ensure exactly 1.0 due to discretization errors
        if weights.sum() > 0:
            weights = weights / weights.sum()
            
        return weights
