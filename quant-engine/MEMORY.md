# Agent Knowledge Graph & Protocols

### Pattern: DuckDB Concurrency Lock
* **Trigger:** When initializing `DuckDBRepo` or encountering `IO Error: Cannot open file` / `database is locked`.
* **Solution:** Implement a `try...finally` block in `orchestrator.py` or the calling script that ensures `self.repo.close()` is called explicitly in the `finally` clause, or ensure the class is used as a context manager: `with DuckDBRepo(...) as repo:`.
* **Verification:** Run `python quant-engine/swarm_daemon.py` and observe for "Zombie Sweeper" logs.

### Pattern: Pandas Timestamp JSON Serialization
* **Trigger:** When passing `macro_context` or `alt_context` (containing Pandas/Numpy types) to an LLM agent/swarm.
* **Solution:** Use the custom encoder: `json.dumps(data, cls=QuantJSONEncoder)`. Do not use standard `json.dumps`.
* **Verification:** Verify signal data generation in `src/execution/llm_agent.py` logs.

### Pattern: Pydantic Validation Guards
* **Trigger:** When building new API clients or data ingestion interfaces.
* **Solution:** Utilize standard type hints (`int`, `str`, `float`, `pd.DataFrame`) and ensure the first method operation is a validation check against the internal `EQUITY_SCHEMA` or `MACRO_SCHEMA`.
* **Verification:** Run `python -m ruff check <file>` and ensure type hint coverage is high.

### Pattern: Swarm Subprocess Invocation
* **Trigger:** When invoking `hermes-agent` or other external tools from `src/execution/`.
* **Solution:** Use `subprocess.run(["python", "-m", "hermes_agent", "-q", prompt], ...)` instead of hardcoded paths.
* **Verification:** Execute `get_signal_data` in `llm_agent.py` and inspect `result.returncode`.
