
import asyncio
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from loguru import logger
import duckdb
import pandas as pd
import uvicorn
import os
import sys

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.process_utils import kill_zombie_locks

app = FastAPI(title="Darwinian Quant Swarm Dashboard")
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "ui" / "templates"))

DB_PATH = str(BASE_DIR / "storage" / "db" / "quant_data.duckdb")

def get_db_connection(retries=3, delay=1):
    """Attempt to connect to DuckDB with retries for file locks."""
    for i in range(retries):
        try:
            return duckdb.connect(DB_PATH, read_only=True)
        except duckdb.IOException as e:
            if "used by another process" in str(e).lower():
                if i < retries - 1:
                    time.sleep(delay)
                    continue
            raise e

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    try:
        con = get_db_connection()
        
        # 1. Swarm Stats
        ohlcv_count = con.execute("SELECT count(*) FROM ohlcv_daily").fetchone()[0]
        feature_count = con.execute("SELECT count(*) FROM feature_store").fetchone()[0]
        
        # 2. Latest Signals
        trades_df = con.execute("""
            SELECT ticker, signal_date, ml_weight, llm_weight, final_blended_signal, final_direction, vibe
            FROM paper_trades 
            ORDER BY signal_date DESC 
            LIMIT 20
        """).df()
        
        con.close()
        
        trades = trades_df.to_dict('records')
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "ohlcv_count": ohlcv_count,
            "feature_count": feature_count,
            "trades": trades,
            "status": "LIVE"
        })
    except Exception as e:
        logger.warning(f"Dashboard DB Access Error: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "ohlcv_count": "Busy",
            "feature_count": "Busy",
            "trades": [],
            "status": "DATABASE_LOCKED"
        })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
