from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
import numpy as np

router = APIRouter()

class OptimizationMetrics(BaseModel):
    optimization_id: str
    qubo_variables: int
    annealing_time_ms: float
    classical_time_ms: float
    energy_found: float

class QuantumResponse(BaseModel):
    latest_run: OptimizationMetrics
    trt_inference_latency_ms: float
    energy_landscape_mesh: List[List[float]]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=QuantumResponse)
def get_quantum_ops_telemetry():
    repo = get_repo()
    
    # 1. Fetch latest optimization
    opt_df = repo.con.execute("""
        SELECT optimization_id, qubo_variables, annealing_time_ms, classical_solver_time_ms, global_minimum_energy
        FROM quantum_optimization_ledger
        ORDER BY date DESC LIMIT 1
    """).df()
    
    if not opt_df.empty:
        latest = OptimizationMetrics(
            optimization_id=opt_df['optimization_id'].iloc[0],
            qubo_variables=int(opt_df['qubo_variables'].iloc[0]),
            annealing_time_ms=float(opt_df['annealing_time_ms'].iloc[0]),
            classical_time_ms=float(opt_df['classical_solver_time_ms'].iloc[0]),
            energy_found=float(opt_df['global_minimum_energy'].iloc[0])
        )
    else:
        latest = OptimizationMetrics(
            optimization_id="MOCK_OPT", qubo_variables=128, annealing_time_ms=12.5, classical_time_ms=5000.0, energy_found=-1.45
        )

    # 2. Mock 3D Mesh for Energy Landscape
    # 20x20 grid
    x = np.linspace(-5, 5, 20)
    y = np.linspace(-5, 5, 20)
    X, Y = np.meshgrid(x, y)
    Z = np.sin(np.sqrt(X**2 + Y**2)) # Mock "cratered" landscape
    
    return QuantumResponse(
        latest_run=latest,
        trt_inference_latency_ms=0.48, # TensorRT Target
        energy_landscape_mesh=Z.tolist()
    )
