# Darwinian Quant Swarm Engine (v1.1-Production)

An autonomous, headless quantitative research and paper-trading engine that bridges the gap between statistical momentum and agentic finance.

## 🚀 Key Features

-   **Multi-Agent Swarm (Agentic Finance)**: Simulates an investment committee with specialized personas (Narrative Analyst, Value Contrarian, Growth Maximizer, Risk Sentinel).
-   **Darwinian Meta-Weighting (Janus Layer)**: Dynamically allocates capital between XGBoost momentum models and LLM reasoning based on 30-day rolling Sharpe ratios.
-   **Intelligent Ingestion**:
    -   **Market Data**: High-speed ingestion via `yfinance` into **DuckDB**.
    -   **Macro Data**: Ingests Treasury yields, CPI (Inflation), and M2 (Liquidity) from FRED.
    -   **Alternative Data**: Real-time Google Trends and Wikipedia Pageviews to capture retail attention.
    -   **Intelligent Scraping**: Uses **ScrapeGraphAI** to extract sentiment from unstructured web sources.
-   **Strict Quantitative Rigor**:
    -   Purged Walk-Forward Cross-Validation with Embargo to prevent data leakage.
    -   Stationary feature engineering (Rate-of-Change, Z-Scores).
    -   Vectorized backtesting via `vectorbt` with realistic transaction costs.
-   **Self-Improving Reasoning**: Ingests historical trade "Reflections" and logs a full 5-step Chain of Thought for every decision.

## 🛠 Architecture

-   `orchestrator.py`: The 5-phase research pipeline (Ingest → Engineer → Train → Backtest → Paper Trade).
-   `swarm_daemon.py`: Background loop for continuous execution and self-healing zombie-process recovery.
-   `dashboard.py`: CLI-based TUI for real-time swarm monitoring.
-   `src/data/`: Modular clients for all data providers.
-   `src/execution/llm_agent.py`: The "Brain" of the swarm reasoning loop.

## 📦 Setup

1. Install dependencies:
   ```bash
   pip install duckdb pandas numpy xgboost optuna vectorbt loguru pandas-datareader pytrends pageviewapi scrapegraphai psutil pyyaml
   ```
2. Run the pipeline:
   ```bash
   python orchestrator.py
   ```
3. Run the continuous daemon:
   ```bash
   python swarm_daemon.py
   ```
4. Monitor the dashboard:
   ```bash
   python dashboard.py
   ```

## ⚖ License
MIT
