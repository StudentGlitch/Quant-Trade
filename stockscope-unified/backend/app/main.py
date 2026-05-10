from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List
import random
import time
from datetime import datetime
from .database import engine, get_session
from .models import FinancialReport, FinancialReportRead, LiveTickerResponse, FinancialFact, CrawlLog
from .auth import get_current_user, NextAuthJWTPayload
from .scoring import ScoringEngine
from .endpoints import screener, portfolio, performance, evolution, cio_desk, fundamentals, osint, live_trading

# Future: Import crawler engine when dependencies are fully resolved
# from .crawler.engine.async_engine import AsyncCrawlEngine

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="Stockscope Unified API - Production")

import sys
from pathlib import Path
# Add quant-engine to path to import telemetry and core APIs
QUANT_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "quant-engine"
sys.path.append(str(QUANT_ENGINE_DIR))

from src.utils.telemetry import router as telemetry_router
from src.api.endpoints import auth_router, external_api, billing, client_webhooks, incoming_webhooks, perception, global_macro, federated_network, derivatives, hydration, mlops, war_room, llm_ops, system_health, time_machine, war_games, quantum_ops
from src.api.core.rate_limiter import limiter

# Configure SlowAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include new routers
app.include_router(screener.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")
app.include_router(evolution.router, prefix="/api/v1")
app.include_router(cio_desk.router, prefix="/api/v1")
app.include_router(fundamentals.router, prefix="/api/v1")
app.include_router(osint.router, prefix="/api/v1")
app.include_router(live_trading.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(external_api.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(client_webhooks.router, prefix="/api/v1")
app.include_router(incoming_webhooks.router, prefix="/api/v1")
app.include_router(perception.router, prefix="/api/v1/perception", tags=["Perception"])
app.include_router(global_macro.router, prefix="/api/v1/global-macro", tags=["Global Macro"])
app.include_router(federated_network.router, prefix="/api/v1/federated-network", tags=["Federated Network"])
app.include_router(derivatives.router, prefix="/api/v1/derivatives", tags=["Derivatives"])
app.include_router(hydration.router, prefix="/api/v1/hydration", tags=["Data Hydration"])
app.include_router(mlops.router, prefix="/api/v1/mlops", tags=["MLOps"])
app.include_router(war_room.router, prefix="/api/v1/war-room", tags=["War Room"])
app.include_router(llm_ops.router, prefix="/api/v1/llm-ops", tags=["LLM Ops"])
app.include_router(system_health.router, prefix="/api/v1/system-health", tags=["System Health"])
app.include_router(time_machine.router, prefix="/api/v1/time-machine", tags=["Time Machine"])
app.include_router(war_games.router, prefix="/api/v1/war-games", tags=["War Games"])
app.include_router(quantum_ops.router, prefix="/api/v1/quantum", tags=["Quantum Ops"])
app.include_router(telemetry_router) # Unprefixed so /metrics is at root

@app.get("/meta.json")
def get_mcp_meta():
    """Endpoint for MCP/AI SDK metadata discovery."""
    return {"status": "ok", "mcp_enabled": True}


# In production, we restrict origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/reports/{ticker}", response_model=List[FinancialReportRead])
def get_reports(
    ticker: str, 
    session: Session = Depends(get_session),
    current_user: NextAuthJWTPayload = Depends(get_current_user)
):
    statement = select(FinancialReport).where(FinancialReport.ticker == ticker.upper())
    results = session.exec(statement).all()
    if not results:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return results

@app.get("/api/v1/ticker/{ticker}/live", response_model=LiveTickerResponse)
def get_live_ticker(
    ticker: str,
    current_user: NextAuthJWTPayload = Depends(get_current_user)
):
    # Simulate live market data
    base_price = 5000 if ticker.upper() == "WAPO" else 1500
    price = base_price + random.uniform(-50, 50)
    return {
        "ticker": ticker.upper(),
        "current_price": round(price, 2),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/crawler/start/{ticker}")
async def start_crawler(
    ticker: str,
    background_tasks: BackgroundTasks,
    current_user: NextAuthJWTPayload = Depends(get_current_user)
):
    # In a real app, check for admin role in JWT
    async def run_crawl_mock():
        print(f"DEBUG: Starting background crawl for {ticker}")
        time.sleep(10)
        print(f"DEBUG: Crawl complete for {ticker}")

    background_tasks.add_task(run_crawl_mock)
    return {"status": "accepted", "message": f"Background crawler initialized for {ticker}"}

@app.get("/api/v1/scoring/{ticker}/{year}")
def get_ticker_score(
    ticker: str,
    year: int,
    session: Session = Depends(get_session),
    current_user: NextAuthJWTPayload = Depends(get_current_user)
):
    engine = ScoringEngine()
    score = engine.calculate_piotroski_f_score(ticker.upper(), year)
    return {
        "ticker": ticker.upper(),
        "year": year,
        "piotroski_f_score": score,
        "max_score": 9
    }

@app.get("/")
def read_root():
    return {"status": "Stockscope Unified API is running in Production Mode (Secure)"}
