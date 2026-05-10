from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo

router = APIRouter()

class FinetuningRun(BaseModel):
    run_id: str
    start_time: str
    base_model: str
    adapter_name: str
    dataset_size: int
    final_loss: float
    status: str

class PreferencePair(BaseModel):
    pair_id: str
    ticker: str
    margin: float
    chosen_preview: str
    rejected_preview: str

class LLMOpsResponse(BaseModel):
    recent_runs: List[FinetuningRun]
    preference_pairs: List[PreferencePair]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/", response_model=LLMOpsResponse)
def get_llm_ops_status():
    repo = get_repo()
    
    # 1. Fetch recent fine-tuning runs
    runs_df = repo.con.execute("""
        SELECT run_id, start_time, base_model, adapter_name, dataset_size, final_loss, status
        FROM llm_finetuning_runs
        ORDER BY start_time DESC LIMIT 5
    """).df()
    
    recent_runs = []
    for _, row in runs_df.iterrows():
        recent_runs.append(FinetuningRun(
            run_id=row['run_id'][:8],
            start_time=str(row['start_time']),
            base_model=row['base_model'],
            adapter_name=row['adapter_name'],
            dataset_size=int(row['dataset_size']),
            final_loss=float(row['final_loss']),
            status=row['status']
        ))

    # 2. Fetch preference dataset sample
    pairs_df = repo.con.execute("""
        SELECT pair_id, ticker, chosen_response, rejected_response, margin_of_victory
        FROM dpo_preference_dataset
        ORDER BY ABS(margin_of_victory) DESC LIMIT 10
    """).df()
    
    preference_pairs = []
    for _, row in pairs_df.iterrows():
        preference_pairs.append(PreferencePair(
            pair_id=row['pair_id'][:8],
            ticker=row['ticker'],
            margin=float(row['margin_of_victory']),
            chosen_preview=str(row['chosen_response'])[:100] + "...",
            rejected_preview=str(row['rejected_response'])[:100] + "..."
        ))
        
    return LLMOpsResponse(
        recent_runs=recent_runs,
        preference_pairs=preference_pairs
    )
