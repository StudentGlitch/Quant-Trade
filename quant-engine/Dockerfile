FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . .

# Install dependencies (ignoring local virtualenvs)
RUN uv pip install --system playwright beautifulsoup4 lxml networkx pandas numpy scipy duckdb pydantic loguru pyyaml requests prometheus-client fastapi uvicorn sqlmodel joblib xgboost scikit-learn

# Expose FastAPI port
EXPOSE 8000

# Default entrypoint for backend
CMD ["uvicorn", "stockscope-unified.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
