# Agent Context Anchor: micro-bounty-swarm

## 1. Project Objective
Orchestrator for decentralized agentic tasks and bounty management.

## 2. Technical Stack
* Language: Python 3.11+
* Frameworks: Custom Swarm Orchestrator
* Package Manager: `uv`

## 3. Key Entry Points
* Main Execution: `uv run python main_orchestrator.py`
* Test Runner: `pytest`

## 4. Specific Conventions
* Task artifacts must be stored in `/artifacts` before any state transition.
* Use the provided `schema.sql` for all persistent state.
