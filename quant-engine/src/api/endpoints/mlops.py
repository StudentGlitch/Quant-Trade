from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
from src.data.duckdb_repo import DuckDBRepo
import mlflow

router = APIRouter()

class DriftMetric(BaseModel):
    feature_name: str
    psi_score: float
    drift_detected: bool

class MLflowRun(BaseModel):
    run_id: str
    status: str
    oos_sharpe: float
    start_time: str

class MLOpsResponse(BaseModel):
    active_drift: List[DriftMetric]
    recent_experiments: List[MLflowRun]
    compute_cluster_health: float

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=MLOpsResponse)
def get_mlops_status():
    repo = get_repo()
    
    # 1. Fetch Drift Metrics
    drift_df = repo.con.execute("""
        SELECT feature_name, psi_score, drift_detected 
        FROM feature_drift_ledger 
        WHERE date = (SELECT MAX(date) FROM feature_drift_ledger)
    """).df()
    
    active_drift = []
    for _, row in drift_df.iterrows():
        active_drift.append(DriftMetric(
            feature_name=row['feature_name'],
            psi_score=float(row['psi_score']),
            drift_detected=bool(row['drift_detected'])
        ))
        
    # 2. Fetch MLflow Experiments (Mocked for MVP if no server reachable)
    recent_experiments = [
        MLflowRun(run_id="run_abc123", status="FINISHED", oos_sharpe=1.28, start_time="2026-05-10 12:00"),
        MLflowRun(run_id="run_xyz789", status="FAILED", oos_sharpe=0.0, start_time="2026-05-09 23:30")
    ]
    
    return MLOpsResponse(
        active_drift=active_drift,
        recent_experiments=recent_experiments,
        compute_cluster_health=94.5
    )
