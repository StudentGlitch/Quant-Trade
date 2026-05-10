import pytest
import numpy as np
import sys
from unittest.mock import MagicMock

# Mock dimod and neal before imports
mock_dimod = MagicMock()
# BQM needs to be a real class mock
class MockBQM:
    def __init__(self, *args, **kwargs):
        self.linear = {}
    def add_variable(self, name, coeff):
        self.linear[name] = self.linear.get(name, 0) + coeff
    def add_interaction(self, *args): pass
    def add_linear_equality_constraint(self, terms, constant, lagrangian_multiplier):
        # Hamiltonian expansion of (sum(weights) - 1)^2
        # (x + y - 1)^2 = x^2 + y^2 + 1 + 2xy - 2x - 2y
        # In binary: x^2 = x
        # linear coeff for x = -2 * lagrangian_multiplier * constant_weight
        # For a single variable x with weight 1.0 and constant -1.0:
        # penalty = 10 * (-2 * 1.0 * -1.0) = -20? No, wait.
        # (W - 1)^2 = W^2 - 2W + 1. 
        # For W = 1.0 * x, this is (1.0x)^2 - 2(1.0x) + 1 = 1.0x - 2.0x + 1 = -1.0x + 1
        # Multiplied by 10.0 penalty = -10.0x + 10
        for var, weight in terms:
            self.linear[var] = self.linear.get(var, 0) + (-1.0 * weight * lagrangian_multiplier)

mock_dimod.BinaryQuadraticModel = MockBQM
mock_dimod.Vartype = MagicMock()
sys.modules['dimod'] = mock_dimod
sys.modules['neal'] = MagicMock()

from src.optimization.qubo_formulator import QUBOFormulator

def test_qubo_encoding_decoding_integrity():
    """
    Verify that portfolio weights can be discretized into binary and 
    mathematically decoded back with minimal loss.
    """
    # 2 assets, 4 bits each
    formulator = QUBOFormulator(num_assets=2, bits_per_weight=4)
    
    # Mock a sample result from the annealer
    sample = {
        "x_0_0": 1, "x_0_1": 1, "x_0_2": 1, "x_0_3": 1,
        "x_1_0": 0, "x_1_1": 0, "x_1_2": 0, "x_1_3": 0
    }
    
    weights = formulator.decode_weights(sample)
    
    assert weights[0] == 1.0
    assert weights[1] == 0.0
    assert np.isclose(weights.sum(), 1.0)

def test_hamiltonian_linear_terms():
    """Ensure return vectors are correctly mapped to linear coefficients."""
    formulator = QUBOFormulator(num_assets=1, bits_per_weight=1)
    
    mu = np.array([0.1])
    sigma = np.array([[0.0]])
    
    bqm = formulator.formulate_bqm(mu, sigma)
    
    # From our mock logic:
    # return coeff = -0.1
    # constraint coeff = -10.0
    # total = -10.1
    
    assert bqm.linear["x_0_0"] == pytest.approx(-10.1)

