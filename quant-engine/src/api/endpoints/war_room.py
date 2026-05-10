import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from src.data.duckdb_repo import DuckDBRepo
from src.execution.war_room_graph import WarRoomGraph

router = APIRouter()

def get_repo() -> DuckDBRepo:
    return DuckDBRepo("storage/db/quant_data.duckdb")

@router.get("/stream/{ticker}")
async def stream_war_room_debate(ticker: str):
    """
    Phase 26.3: SSE Endpoint for Live Debate Streaming.
    """
    repo = get_repo()
    graph = WarRoomGraph(repo)

    async def event_generator():
        # Yield initial message
        yield f"data: {json.dumps({'role': 'System', 'content': f'Initiating War Room for {ticker}'})}\n\n"
        await asyncio.sleep(1)

        # In a real LangGraph setup with streaming, we would use graph.astream()
        # For MVP we will mock the stream steps
        
        roles = ["Quant_Agent", "Macro_Agent", "Risk_Agent", "Rebuttal", "CIO_Agent"]
        
        # Actually run it (synchronously in MVP, or mock async steps)
        # To simulate SSE streaming, we'll yield mock steps
        yield f"data: {json.dumps({'role': 'Quant Dev', 'content': 'Given the XGBoost momentum and IV skew, I vote STRONG_BUY (1.0).'})}\n\n"
        await asyncio.sleep(1)
        
        yield f"data: {json.dumps({'role': 'Macro Economist', 'content': 'VAR models indicate liquidity contraction. I vote HOLD (0.0).'})}\n\n"
        await asyncio.sleep(1)
        
        yield f"data: {json.dumps({'role': 'Risk Manager', 'content': 'Tail risk is elevated. Delta is neutral. I vote STRONG_SELL (-1.0).'})}\n\n"
        await asyncio.sleep(1)
        
        yield f"data: {json.dumps({'role': 'Rebuttal', 'content': 'The macro data is lagging.'})}\n\n"
        await asyncio.sleep(1)
        
        # Calculate C_final mock
        c_final = (0.2 * 1.0 + 0.9 * 0.0 + 0.5 * -1.0) / (0.2 + 0.9 + 0.5) # Mock math
        decision = "HOLD"
        
        yield f"data: {json.dumps({'role': 'CIO', 'content': f'Final Decision: {decision} (Conviction: {c_final:.2f})'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/history/{ticker}")
def get_debate_history(ticker: str):
    repo = get_repo()
    df = repo.con.execute("""
        SELECT debate_id, date, transcript, final_decision, blended_conviction 
        FROM war_room_transcripts 
        WHERE ticker = ? 
        ORDER BY date DESC LIMIT 5
    """, [ticker]).df()
    
    # Return parsed json
    results = []
    for _, row in df.iterrows():
        results.append({
            "debate_id": row["debate_id"],
            "date": str(row["date"]),
            "transcript": json.loads(row["transcript"]) if row["transcript"] else [],
            "final_decision": row["final_decision"],
            "blended_conviction": row["blended_conviction"]
        })
    return results
