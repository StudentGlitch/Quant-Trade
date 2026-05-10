import pytest
import math
from unittest.mock import MagicMock
from src.execution.war_room_graph import WarRoomGraph

def test_accuracy_weighted_voting():
    """
    Test accuracy-weighted Softmax conviction logic (PRD 7.1).
    Macro (Acc: 0.9) votes +1.0. Quant (Acc: 0.2) votes -1.0.
    C_final should strongly favor the Macro agent.
    """
    repo = MagicMock()
    war_room = WarRoomGraph(repo)
    
    # Mock State
    state = {
        "ticker": "BBCA",
        "data_context": "mock data",
        "messages": [],
        "votes": {
            "MACRO_ECONOMIST": 1.0,
            "QUANT_DEV": -1.0,
            "RISK_MANAGER": 0.0
        },
        "iteration": 1
    }
    
    # Run the CIO synthesis node which handles the math
    result_state = war_room.cio_node(state)
    
    c_final = result_state["final_conviction"]
    decision = result_state["final_decision"]
    
    # Expected Softmax Math
    # exp(0.9) ~ 2.459
    # exp(0.2) ~ 1.221
    # exp(0.5) ~ 1.648
    # Sum ~ 5.328
    # w_macro ~ 0.46
    # w_quant ~ 0.23
    # w_risk ~ 0.31
    # c_final = (0.46 * 1.0) + (0.23 * -1.0) + (0.31 * 0.0) = 0.46 - 0.23 = 0.23
    # Wait, my manual math above is an approximation. Let's let the actual code calculate it.
    
    # It should be positive because Macro's weight is much higher than Quant's
    assert c_final > 0.0
    
    # Exact calculation
    accuracies = {"QUANT_DEV": 0.2, "MACRO_ECONOMIST": 0.9, "RISK_MANAGER": 0.5}
    exp_sum = sum([math.exp(a) for a in accuracies.values()])
    w_macro = math.exp(0.9) / exp_sum
    w_quant = math.exp(0.2) / exp_sum
    w_risk = math.exp(0.5) / exp_sum
    
    expected_c_final = (w_macro * 1.0) + (w_quant * -1.0) + (w_risk * 0.0)
    
    assert abs(c_final - expected_c_final) < 1e-6
    
    # Check that repo was called to save transcript
    assert repo.con.execute.called
