# Global Engineering Protocols: Algo Trade Workspace

## Overview
This workspace contains multiple autonomous systems (`quant-engine`, `stockscope-unified`, `micro-bounty-swarm`). These protocols ensure architectural parity across all projects.

## Global Standards
1. **Surgical Completeness:** Fix only what is tasked. No "while-at-it" refactors unless they are blocking.
2. **Lean-by-Default:** No unused imports, no zombie dependencies (check `README.md`), and no speculative code.
3. **Mandatory Validation:** Every change must pass `ruff check` (linting) and `py_compile` (syntax). New logic requires a `pytest` file in the project's `tests/` directory.

## Cross-Repo Tooling
- **Pre-Flight Check:** Before working on any repo, run `python <repo_root>/src/utils/pre_flight.py <target_file>`.
- **Knowledge Recall:** Always consult the local `MEMORY.md` in the repository root for domain-specific patterns.

## Repository Map
- `/quant-engine`: Quantitative research, backtesting, and swarm execution.
- `/stockscope-unified`: Unified stock market data ingestion & normalization.
- `/micro-bounty-swarm`: Distributed agentic task execution and orchestration.
- `/Experiment`: R&D sandboxes and specialized web crawlers (Do not import logic directly; use as reference or build native tools).

## Operational Workflow
1. **Search:** Check local `MEMORY.md` patterns.
2. **Analyze:** Run `pre_flight.py` to identify technical debt and gaps.
3. **Template:** Use `docs/global/templates/` for standard structures.
4. **Validate:** `ruff` + `pytest`.
5. **Commit:** Follow standardized commit prefixes (`chore:`, `fix:`, `feat:`).
