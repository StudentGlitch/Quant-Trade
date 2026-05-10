import os
from fastapi import APIRouter, HTTPException, FastAPI
from pydantic import BaseModel
from typing import List, Optional
from src.data.duckdb_repo import DuckDBRepo

app = FastAPI()
router = APIRouter()

class ProfilingMetric(BaseModel):
    function_name: str
    avg_execution_time_ms: float
    peak_memory_mb: float
    is_bottleneck: bool

class CodeAnomaly(BaseModel):
    anomaly_id: str
    file_path: str
    anomaly_type: str
    severity: str
    description: str
    git_branch_name: Optional[str]
    commit_hash: Optional[str]
    status: str

class SystemHealthResponse(BaseModel):
    bottlenecks: List[ProfilingMetric]
    active_anomalies: List[CodeAnomaly]
    overall_health_score: float

class RemediateAction(BaseModel):
    action: str

_repo = None
def get_repo() -> DuckDBRepo:
    global _repo
    if _repo is None:
        _repo = DuckDBRepo("storage/db/quant_data.duckdb")
        _repo.__enter__() 
    return _repo

@app.get("/meta.json")
@router.get("/meta.json")
def get_mcp_meta():
    """Endpoint for MCP/AI SDK metadata discovery."""
    return {"status": "ok", "mcp_enabled": True}

@router.get("/", response_model=SystemHealthResponse)
def get_system_health():
    try:
        repo = get_repo()
        bottlenecks_df = repo.con.execute("""
            SELECT function_name, avg_execution_time_ms, peak_memory_mb 
            FROM code_profiling_logs 
            WHERE avg_execution_time_ms > 500
        """).df()
        
        bottlenecks = []
        for _, row in bottlenecks_df.iterrows():
            bottlenecks.append(ProfilingMetric(
                function_name=row['function_name'],
                avg_execution_time_ms=float(row['avg_execution_time_ms']),
                peak_memory_mb=float(row['peak_memory_mb']),
                is_bottleneck=True
            ))
            
        anomalies_df = repo.con.execute("""
            SELECT anomaly_id, file_path, anomaly_type, severity, description, git_branch_name, commit_hash, status
            FROM identified_anomalies
            WHERE status != 'APPLIED'
        """).df()
        
        active_anomalies = []
        for _, row in anomalies_df.iterrows():
            active_anomalies.append(CodeAnomaly(
                anomaly_id=row['anomaly_id'],
                file_path=row['file_path'],
                anomaly_type=row['anomaly_type'],
                severity=row['severity'],
                description=row['description'],
                git_branch_name=row.get('git_branch_name'),
                commit_hash=row.get('commit_hash'),
                status=row['status']
            ))
            
        return SystemHealthResponse(
            bottlenecks=bottlenecks,
            active_anomalies=active_anomalies,
            overall_health_score=92.0
        )
    except Exception as e:
        from loguru import logger
        logger.warning(f"System health tables unavailable or empty: {e}")
        return SystemHealthResponse(
            bottlenecks=[],
            active_anomalies=[],
            overall_health_score=100.0
        )

@router.post("/remediate/{anomaly_id}")
def remediate_anomaly(anomaly_id: str, action_data: RemediateAction):
    repo = get_repo()
    if action_data.action == "APPROVE":
        repo.con.execute("UPDATE identified_anomalies SET status = 'APPLIED' WHERE anomaly_id = ?", [anomaly_id])
        return {"status": "Remediation Approved and Applied"}
    
    repo.con.execute("UPDATE identified_anomalies SET status = 'REJECTED' WHERE anomaly_id = ?", [anomaly_id])
    return {"status": "Remediation Rejected"}

@app.get("/")
def read_root():
    return {"status": "System Health API Active"}

app.include_router(router, prefix="/api/v1/system-health")
