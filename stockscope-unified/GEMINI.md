# Agent Context Anchor: stockscope-unified

## 1. Project Objective
Integrated platform providing financial data visualization and algorithmic stock screening.

## 2. Technical Stack
* Language: Python 3.11+, TypeScript
* Frameworks: FastAPI, SQLModel, Next.js 16, React 19, Tailwind 4
* Package Manager: `uv`

## 3. Key Entry Points
* API Backend: `uv run python backend/app/main.py`
* Frontend: `cd frontend && npm run dev`
* Test Runner: `pytest`

## 4. Specific Conventions
* All database interactions MUST use SQLModel sessions.
* UI components must adhere to Tailwind 4 design patterns.
