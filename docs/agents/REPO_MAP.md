# Agent Context: quant-engine Repository

## Overview
The `quant-engine` is an autonomous, headless quantitative research and paper-trading engine. It bridges statistical momentum with agentic financial reasoning.

## Core Architecture
- **Orchestration:** Controlled by `orchestrator.py` (Phase 1-5 pipeline).
- **Execution:** LLM-enhanced reasoning via `src/execution/llm_agent.py` and `swarm_daemon.py`.
- **Data:** DuckDB-backed storage with modular clients in `src/data/`.
- **UI:** TUI-based dashboard in `src/ui/`.
- **Math/Metrics:** Utility functions for quantitative analysis in `src/utils/`.

## Key Directories
- `src/data/`: Data ingestion (Yahoo Finance, FRED Macro, Alternative Data).
- `src/execution/`: Swarm logic and agent orchestration.
- `src/models/`: Quantitative models (XGBoost trainers, Janus Blender).
- `src/utils/`: Math utilities, metrics, and JSON handling.
- `tests/`: Unit and integration tests (using pytest).
- `storage/`: Parquet and DuckDB storage.

## Operational Standards
- **Standard:** Surgical completeness, "lean-by-default," and strict adherence to `pytest` verification for all code changes.
- **Tools:** Use `ruff` for linting and `py_compile` for syntax checks.
