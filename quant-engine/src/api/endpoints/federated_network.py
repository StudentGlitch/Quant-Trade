from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
from datetime import datetime

router = APIRouter()

class EdgeNodeTelemetry(BaseModel):
    node_id: str
    status: str
    training_rounds: int
    alpha_contribution: float
    last_ping: str

class FederatedRoundStats(BaseModel):
    round_id: int
    nodes_participated: int
    loss_improvement_pct: float

class FederatedNetworkResponse(BaseModel):
    active_nodes: List[EdgeNodeTelemetry]
    recent_rounds: List[FederatedRoundStats]
    global_network_health: float

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=FederatedNetworkResponse)
def get_federated_network_status():
    repo = get_repo()
    
    # Fetch Active Nodes
    nodes_df = repo.con.execute("""
        SELECT node_id, status, total_training_rounds, alpha_contribution_score, last_ping
        FROM federated_nodes_ledger
        ORDER BY alpha_contribution_score DESC
        LIMIT 20
    """).df()
    
    active_nodes = []
    for _, row in nodes_df.iterrows():
        active_nodes.append(EdgeNodeTelemetry(
            node_id=row['node_id'],
            status=row['status'],
            training_rounds=int(row['total_training_rounds']),
            alpha_contribution=float(row['alpha_contribution_score']),
            last_ping=str(row['last_ping'])
        ))

    # Fetch Recent Rounds
    rounds_df = repo.con.execute("""
        SELECT round_id, nodes_participated, global_model_loss_before, global_model_loss_after
        FROM training_rounds_ledger
        ORDER BY start_time DESC
        LIMIT 5
    """).df()
    
    recent_rounds = []
    for _, row in rounds_df.iterrows():
        before = float(row['global_model_loss_before'])
        after = float(row['global_model_loss_after'])
        improvement = ((before - after) / before) * 100 if before > 0 else 0.0
        
        recent_rounds.append(FederatedRoundStats(
            round_id=int(row['round_id']),
            nodes_participated=int(row['nodes_participated']),
            loss_improvement_pct=improvement
        ))
        
    return FederatedNetworkResponse(
        active_nodes=active_nodes,
        recent_rounds=recent_rounds,
        global_network_health=98.5
    )
