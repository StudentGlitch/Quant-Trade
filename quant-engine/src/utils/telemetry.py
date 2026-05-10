from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter
from fastapi.responses import Response

# 1. Define Metrics
# Counter tracking total Hermes LLM tokens consumed
SWARM_LLM_TOKENS_TOTAL = Counter(
    'swarm_llm_tokens_total', 
    'Total number of tokens consumed by the Hermes LLM Agent Cohort',
    ['agent_role', 'task_type']
)

# Counter tracking successful Phase 8 extractions
SWARM_OSINT_SCRAPES_SUCCESS = Counter(
    'swarm_osint_scrapes_success',
    'Total number of successful OSINT extractions',
    ['dataset_id']
)

# Gauge tracking the real-time Value at Risk
SWARM_PORTFOLIO_VAR = Gauge(
    'swarm_portfolio_var',
    'Current 1-Day Value at Risk (99%) for the simulated portfolio'
)

# 2. FastAPI Endpoint for Prometheus Scraping
router = APIRouter()

@router.get("/metrics")
def get_metrics():
    """
    Phase 9.3: Telemetry & Observability.
    Expose Prometheus metrics for Grafana visualization.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# 3. Helper functions to update metrics from within the Quant Engine
class TelemetryManager:
    @staticmethod
    def record_llm_usage(agent_role: str, task_type: str, tokens: int):
        SWARM_LLM_TOKENS_TOTAL.labels(agent_role=agent_role, task_type=task_type).inc(tokens)
        
    @staticmethod
    def record_scraper_success(dataset_id: str):
        SWARM_OSINT_SCRAPES_SUCCESS.labels(dataset_id=dataset_id).inc()
        
    @staticmethod
    def update_portfolio_var(var_value: float):
        SWARM_PORTFOLIO_VAR.set(var_value)
