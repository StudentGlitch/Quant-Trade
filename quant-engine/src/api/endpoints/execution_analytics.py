from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.data.duckdb_repo import DuckDBRepo
from datetime import datetime

router = APIRouter()

class ChildExecution(BaseModel):
    execution_time: datetime
    executed_quantity: int
    executed_price: float
    market_impact: float

class ParentTrajectory(BaseModel):
    parent_id: str
    ticker: str
    total_quantity: int
    actual_average_price: float
    target_vwap: float
    slippage_savings_bps: float
    child_executions: List[ChildExecution]

class ExecutionAnalyticsResponse(BaseModel):
    recent_trajectories: List[ParentTrajectory]
    overall_drl_savings_idr: float

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=ExecutionAnalyticsResponse)
def get_execution_analytics():
    repo = get_repo()
    
    # 1. Fetch Recent Parent Orders
    parents_df = repo.con.execute("""
        SELECT parent_id, ticker, total_quantity, target_vwap, actual_average_price, drl_slippage_savings
        FROM parent_orders
        ORDER BY start_time DESC
        LIMIT 10
    """).df()
    
    trajectories = []
    for _, prow in parents_df.iterrows():
        # Fetch Children for this parent
        children_df = repo.con.execute("""
            SELECT execution_time, executed_quantity, executed_price, market_impact_incurred
            FROM child_orders
            WHERE parent_id = ?
            ORDER BY execution_time ASC
        """, [prow['parent_id']]).df()
        
        children = []
        for _, crow in children_df.iterrows():
            children.append(ChildExecution(
                execution_time=crow['execution_time'],
                executed_quantity=int(crow['executed_quantity']),
                executed_price=float(crow['executed_price']),
                market_impact=float(crow['market_impact_incurred'])
            ))
            
        trajectories.append(ParentTrajectory(
            parent_id=prow['parent_id'],
            ticker=prow['ticker'],
            total_quantity=int(prow['total_quantity']),
            actual_average_price=float(prow['actual_average_price']),
            target_vwap=float(prow['target_vwap']) if prow['target_vwap'] else prow['actual_average_price'],
            slippage_savings_bps=float(prow['drl_slippage_savings']),
            child_executions=children
        ))
        
    return ExecutionAnalyticsResponse(
        recent_trajectories=trajectories,
        overall_drl_savings_idr=125000000.0 # Mock aggregate savings
    )
