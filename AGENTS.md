# AGENTS.md — Workspace Guide for AI Agents

## Purpose

This folder is a **multi-project Indonesian market intelligence + algo trading workspace**.  
Treat each top-level directory as an independent project unless explicitly asked to integrate them.

## Project Map (Start Here)

1. `stockscope-unified`  
   - Main integrated app.  
   - `backend`: FastAPI + SQLModel API (`backend/app/main.py`).  
   - `frontend`: Next.js 16 + React 19 (`frontend/README.md`, `frontend/package.json`).

2. `StockscopeV2`  
   - Older/experimental stack.  
   - `indonesia-stock-screener`: API/web monorepo.  
   - `idx_experiment`: async JKSE crawler v2 (`crawler_v2/main.py`).  
   - `stitch_idx_institutional_terminal`: terminal UI design system.

3. `Tugas Akhir`  
   - Quant research + MLOps + paper/live trading workflow.  
   - Key scripts in `research/` (train pipeline, trading engine, preflight).

4. `Jojo`  
   - Financial statement extraction from PDFs using OCR + Gemini API.  
   - Data-heavy folder (many `.xlsx`/`.csv` files).

5. `Experiment`  
   - Python package `webcrawler` with CLI + remote SSH crawl support.

6. `hermes-agent`  
   - Separate full AI agent platform repo (large, independent codebase).

## Recommended Entry Points by Task

- API/backend changes: `stockscope-unified\backend\app\main.py`
- Frontend/UI changes: `stockscope-unified\frontend`
- Crawler reliability/performance: `StockscopeV2\indonesia-stock-screener\idx_experiment\crawler_v2`
- Trading strategy/pipeline: `Tugas Akhir\research`
- PDF financial extraction: `Jojo\extract_financials.py`

## Working Rules for Agents

- Confirm target subproject before editing; this workspace has overlapping themes and duplicate concepts.
- Prefer surgical changes; avoid cross-project refactors unless requested.
- Keep secrets out of commits (`.env`, API keys, credentials).
- Expect large local data artifacts; avoid mass scanning binary files unless needed.
- If ambiguity exists, default to `stockscope-unified` as the primary active app.

## Quick Context Snapshot

- Dominant languages: **Python**, **TypeScript/JavaScript**.
- Common stacks: FastAPI, SQLModel/SQLAlchemy, Next.js 16, React 19, Tailwind 4, Playwright, pandas/numpy.
- Infra style: mixed local DB files + env-based DB URLs + Docker compose in some projects.
