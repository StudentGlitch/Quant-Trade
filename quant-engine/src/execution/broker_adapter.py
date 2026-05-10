from abc import ABC, abstractmethod
from loguru import logger
import uuid
import asyncio

class BaseBrokerAdapter(ABC):
    """Abstract interface for external broker APIs."""
    
    @abstractmethod
    def get_account_balance(self) -> float:
        pass
        
    @abstractmethod
    def get_positions(self) -> dict:
        pass
        
    @abstractmethod
    async def place_market_order(self, ticker: str, quantity: int, order_type: str) -> dict:
        pass

class MockIndonesianBrokerAdapter(BaseBrokerAdapter):
    """
    Phase 10.1: Concrete mock implementation of a live REST API.
    Allows safe testing before real credentials are injected.
    """
    
    def __init__(self, credentials: dict):
        self.api_key = credentials.get("api_key")
        self._mock_balance = 100_000_000.0
        self._mock_positions = {}
        
    def get_account_balance(self) -> float:
        # Simulating REST API call
        return self._mock_balance
        
    def get_positions(self) -> dict:
        # Simulating REST API call
        return self._mock_positions
        
    async def place_market_order(self, ticker: str, quantity: int, order_type: str) -> dict:
        """Simulate placing an order with a live broker."""
        logger.info(f"Broker API: Sending {order_type} order for {quantity} shares of {ticker}")
        
        # Simulate network latency
        await asyncio.sleep(0.5)
        
        order_id = f"LIVE_{uuid.uuid4().hex[:8].upper()}"
        
        # Simulate execution price (just a dummy for testing)
        executed_price = 5000.0 if ticker != 'BBCA.JK' else 9800.0
        
        return {
            "order_id": order_id,
            "status": "FILLED",
            "executed_price": executed_price,
            "quantity": quantity,
            "ticker": ticker,
            "type": order_type
        }
