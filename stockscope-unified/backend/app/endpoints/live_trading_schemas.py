from pydantic import BaseModel
from typing import List

class LiveOrder(BaseModel):
    order_id: str
    ticker: str
    order_type: str
    quantity: int
    status: str
    executed_price: float

class ReconciliationState(BaseModel):
    date: str
    drift_percentage: float
    sync_status: str

class LiveTradingResponse(BaseModel):
    is_live_mode_active: bool
    recent_orders: List[LiveOrder]
    reconciliation: ReconciliationState
