FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv

COPY . .

# Install dependencies (adjust as needed for the micro-bounty-swarm)
# Assuming a requirements.txt or basic dependencies
RUN uv pip install --system playwright beautifulsoup4 loguru duckdb pydantic

# CMD assumes there's an entry point for the headless worker
CMD ["python", "main_orchestrator.py"]
