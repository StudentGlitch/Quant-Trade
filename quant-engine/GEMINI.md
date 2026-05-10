# Agent Context Anchor: quant-engine

## 1. Project Objective
Quant research, vectorized backtesting, and automated trade execution engine.

## 2. Technical Stack
* Language: Python 3.11+
* Frameworks: Pandas, Numpy, Custom Backtesting Library
* Package Manager: `uv`

## 3. Key Entry Points
* Main Execution: `python src/main.py`
* Test Runner: `pytest tests/`

## 4. Specific Conventions
* Vectorization is mandatory for all price-series calculations.
* All trade signals must be logged to the local database before execution.
