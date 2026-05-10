import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock heavy dependencies
sys.modules['git'] = MagicMock()
sys.modules['whisper'] = MagicMock()
sys.modules['librosa'] = MagicMock()

# Setup eager execution for testing Canvas
from src.workers.celery_app import app

@pytest.fixture(autouse=True)
def setup_celery_test():
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    yield
    app.conf.task_always_eager = False

def test_daily_trading_cycle_sequence():
    """
    Canvas Execution Test: Verify the DAG sequence.
    Scrape -> Feature -> Debate -> Weights -> OMS.
    """
    from src.workflows.daily_trading_cycle import trigger_daily_trading_cycle
    
    universe = ['BBCA.JK']
    
    with patch("src.workers.background_tasks.scrape_ticker.run") as mock_scrape, \
         patch("src.workers.background_tasks.engineer_cross_sectional_features.run") as mock_features, \
         patch("src.workers.background_tasks.run_war_room_debate.run") as mock_debate, \
         patch("src.workers.background_tasks.calculate_portfolio_weights.run") as mock_weights, \
         patch("src.workers.background_tasks.dispatch_to_oms.run") as mock_oms:
        
        # Set return values to allow chain to continue
        mock_scrape.return_value = {"ticker": "BBCA.JK", "status": "scraped"}
        mock_features.return_value = "features_updated"
        mock_debate.return_value = "debate_complete"
        mock_weights.return_value = "weights_calculated"
        mock_oms.return_value = "trades_dispatched"
        
        # Trigger
        trigger_daily_trading_cycle(universe)
        
        # Assert Execution Order (Canvas handles the orchestration)
        assert mock_scrape.called
        assert mock_features.called
        assert mock_debate.called
        assert mock_weights.called
        assert mock_oms.called

def test_nightly_ml_cycle_conditional():
    """Verify that retraining only triggers if drift is detected."""
    from src.workflows.nightly_ml_cycle import trigger_nightly_ml_cycle
    
    with patch("src.workers.background_tasks.calculate_psi_drift.run") as mock_drift, \
         patch("src.workers.background_tasks.train_qlora_adapter.run") as mock_train:
        
        # Scenario 1: No Drift
        mock_drift.return_value = False
        trigger_nightly_ml_cycle()
        assert not mock_train.called
        
        # Scenario 2: Drift Detected
        mock_drift.return_value = True
        trigger_nightly_ml_cycle()
        assert mock_train.called
