from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
import uuid
from datetime import datetime
import os

router = APIRouter()

class LPCommitmentRequest(BaseModel):
    user_id: str
    committed_capital_usd: float

class AutoDevPullRequest(BaseModel):
    pr_id: str
    feature_name: str
    improvement_pct: float
    git_branch_name: str
    status: str

class ApexFundState(BaseModel):
    total_aum_usd: float
    active_lps: int
    live_portfolio_sharpe: float
    pending_ai_prs: List[AutoDevPullRequest]

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.post("/commit")
def commit_capital(request: LPCommitmentRequest):
    """Phase 30.3: LP Onboarding Form."""
    repo = get_repo()
    commitment_id = str(uuid.uuid4())
    
    try:
        repo.con.execute("""
            INSERT INTO lp_commitments 
            (commitment_id, user_id, committed_capital_usd, kyc_status, signed_date)
            VALUES (?, ?, ?, 'PENDING', ?)
        """, [commitment_id, request.user_id, request.committed_capital_usd, datetime.now()])
        return {"status": "success", "commitment_id": commitment_id, "message": "Capital commitment received. KYC pending."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard", response_model=ApexFundState)
def get_apex_dashboard():
    """Serves the 'God View' metrics."""
    repo = get_repo()
    
    # 1. Calculate AUM from commitments (Mocked APPROVED status for MVP)
    aum_df = repo.con.execute("""
        SELECT SUM(committed_capital_usd) as total_aum, COUNT(DISTINCT user_id) as active_lps 
        FROM lp_commitments
    """).df()
    
    total_aum = float(aum_df['total_aum'].iloc[0]) if pd.notna(aum_df['total_aum'].iloc[0]) else 5000000.0 # Base 5M seed
    active_lps = int(aum_df['active_lps'].iloc[0]) if pd.notna(aum_df['active_lps'].iloc[0]) else 2
    
    # 2. Fetch pending auto-dev PRs
    prs_df = repo.con.execute("""
        SELECT pr_id, feature_name, improvement_pct, git_branch_name, status 
        FROM autonomous_pr_ledger
        WHERE status = 'PENDING_REVIEW'
        ORDER BY improvement_pct DESC
    """).df()
    
    pending_prs = []
    for _, row in prs_df.iterrows():
        pending_prs.append(AutoDevPullRequest(
            pr_id=row['pr_id'][:8],
            feature_name=row['feature_name'],
            improvement_pct=float(row['improvement_pct']),
            git_branch_name=row['git_branch_name'],
            status=row['status']
        ))
        
    return ApexFundState(
        total_aum_usd=total_aum,
        active_lps=active_lps,
        live_portfolio_sharpe=2.85,
        pending_ai_prs=pending_prs
    )
