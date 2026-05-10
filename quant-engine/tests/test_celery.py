import pytest
from unittest.mock import patch, MagicMock
import sys

# Advanced mock for Celery to pass structural tests without the library
class MockConf:
    def __init__(self):
        self.task_routes = {}
        self.task_acks_late = False
        self.beat_schedule = {}
    
    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockCeleryApp:
    def __init__(self, *args, **kwargs):
        self.conf = MockConf()
        self.name = "mock_celery"
        
    def task(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

# Inject mocks
mock_celery_module = MagicMock()
mock_celery_module.Celery = MockCeleryApp
mock_celery_module.Task = MagicMock

sys.modules['celery'] = mock_celery_module
sys.modules['celery.schedules'] = MagicMock()
sys.modules['git'] = MagicMock()

# Now import
from src.workers.celery_app import app
from src.workers.background_tasks import QuantTask

def test_celery_task_routing_config():
    """Ensure tasks are routed to the correct queues."""
    # Based on the PRD 6.1 configuration requirements
    routes = app.conf.task_routes
    
    assert routes.get('src.workers.background_tasks.execute_trades') == {'queue': 'high_priority'}
    assert routes.get('src.workers.background_tasks.train_models') == {'queue': 'ml_training'}
    assert routes.get('src.workers.background_tasks.scrape_osint') == {'queue': 'scraping'}

def test_celery_acks_late():
    """Fault Tolerance Test: Verify task_acks_late is enabled to prevent data loss on crash."""
    # PRD 8 Validation Requirement
    assert app.conf.task_acks_late is True

def test_quant_task_failure_logging():
    """Ensure the custom base task logs failures."""
    task = QuantTask()
    task.name = "test_task"
    
    with patch("src.workers.background_tasks.logger.error") as mock_logger:
        task.on_failure(Exception("Mock Crash"), "1234", (), {}, None)
        mock_logger.assert_called_once()
        assert "Mock Crash" in mock_logger.call_args[0][0]
