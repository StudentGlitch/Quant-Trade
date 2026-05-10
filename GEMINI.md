# Automated Engineering Protocols (AEP)

These instructions are foundational mandates for Gemini CLI. They prioritize autonomous execution, technical rigor, and the use of specialized workspace tools.

## 1. Core Automation Mandate
- **Direct Action by Default:** Treat every goal-oriented prompt as a **Directive**. Proceed autonomously through Research, Strategy, and Execution.
- **Minimal Intervention:** Use `ask_user` only for critical architectural decisions or financial commitments. For technical trade-offs, act as a Senior Engineer (prioritize robustness, type safety, and error handling).
- **Tool Concurrency:** Execute independent tool calls (e.g., parallel `grep_search`, `read_file`, or tests) in the same turn to maximize efficiency.

## 2. Specialized Toolchain Integration
- **IDX Data Extraction:** For all IDX-related tasks, use `Experiment/webcrawler/idx_reports.py`. It is the primary tool for bypassing Cloudflare via Playwright/Obscura CDP.
- **Orchestration (Hermes):** Use the Hermes Agent (`hermes-agent/cli.py -z`) for complex code reviews, batch processing, or when a "fresh context" subagent is required for a sub-task.
- **Swarm Intelligence (RuFlo):** Follow the `hierarchical-mesh` topology defined in `.claude-flow/config.yaml` for cross-module refactoring and multi-agent coordination.
- **Local Proxy (OpenClaw):** Utilize `openclaw` for managing persistent agent state or bridging with messaging channels for asynchronous notifications.

## 3. Engineering & Implementation Standards
- **Incremental Progress:** Every data-heavy script MUST implement incremental saving (e.g., writing to CSV/DB per-item) to prevent data loss.
- **Ticker Integrity:** All stock-market tasks MUST utilize `ticker_validator.py` to filter out inactive tickers or those with stock splits in the target timeframe.
- **CALK Extraction:** Financial metric extraction must follow the regex-based logic in `calk_extractor.py` to ensure precision across Indonesian/English reports.

## 4. Validation & Persistence
- **Mandatory Verification:** A task is not complete until:
    1. It is empirically verified with a test script or sample run.
    2. Output files (e.g., `reports.csv`) are validated for schema and content.
    3. The code passes a linter check (`python -m ruff check`).
- **Memory Preservation:** After every successful fix or implementation, record the technical pattern in the private `MEMORY.md` index to ensure the agent "learns" from the workspace history.

## 6. Environment Management Standard (Mandatory)
To ensure reproducible and consistent environments, all agents MUST use `uv` for dependency management and script execution. 
- Use `uv pip install -r requirements.txt` for existing projects.
- Use `uv run python script.py` to execute tasks in project-specific environments.
- Do NOT use standard `pip` or `conda` unless explicitly necessary for legacy compatibility.

