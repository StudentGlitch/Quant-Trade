"""
crawler_v2/config.py — Environment-based configuration for the v2 async crawler.

All tunable values come from .env or environment variables (never hard-coded).
"""

import os
from pathlib import Path

import pymysql  # noqa: F401
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).parent
_PROJECT_ROOT = _BASE_DIR.parent

# Load .env from the crawler_v2 directory first, then fall back to jkse-crawler
load_dotenv(_BASE_DIR / ".env", override=False)
load_dotenv(_PROJECT_ROOT / "jkse-crawler" / ".env", override=False)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB: str = os.getenv("MYSQL_DB", "jkse_db")

DATABASE_URL: str = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
)

# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

CRAWLER_V2_CONCURRENCY: int = int(os.getenv("CRAWLER_V2_CONCURRENCY", "10"))
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))

# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------

PROXY_FILE: str = os.getenv("PROXY_FILE", str(_BASE_DIR / "proxies.txt"))
PROXY_TEST_URL: str = os.getenv("PROXY_TEST_URL", "https://httpbin.org/ip")
PROXY_TIMEOUT: int = int(os.getenv("PROXY_TIMEOUT", "10"))
PROXY_ROTATION_MODE: str = os.getenv("PROXY_ROTATION_MODE", "round_robin")
PROXY_MAX_DOMAIN_HITS: int = int(os.getenv("PROXY_MAX_DOMAIN_HITS", "10"))
PROXY_FAIL_THRESHOLD: int = int(os.getenv("PROXY_FAIL_THRESHOLD", "3"))

# ---------------------------------------------------------------------------
# Anti-block / Rate limiting
# ---------------------------------------------------------------------------

CRAWL_DELAY_MIN: float = float(os.getenv("CRAWL_DELAY_MIN", "2"))
CRAWL_DELAY_MAX: float = float(os.getenv("CRAWL_DELAY_MAX", "5"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

# ---------------------------------------------------------------------------
# Gap Detection
# ---------------------------------------------------------------------------

GAP_FILL_PRIORITY_FIELDS: str = os.getenv(
    "GAP_FILL_PRIORITY_FIELDS", "pe_ratio,roe,net_margin"
)
GAP_STALE_DAYS: int = int(os.getenv("GAP_STALE_DAYS", "3"))
GAP_FILL_INTERVAL_HOURS: int = int(os.getenv("GAP_FILL_INTERVAL_HOURS", "6"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# IDX / Yahoo Finance constants
# ---------------------------------------------------------------------------

IDX_BASE_URL: str = "https://www.idx.co.id"
YF_SUFFIX: str = ".JK"
YF_PRICE_PERIOD: str = "5y"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SELECTOR_STORE_PATH: str = os.getenv(
    "SELECTOR_STORE_PATH", str(_BASE_DIR / "selector_store.json")
)
REPORTS_DIR: str = str(_BASE_DIR / "reports")
LOGS_DIR: str = str(_BASE_DIR / "logs")

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

TARGET_SCORE: float = float(os.getenv("V2_TARGET_SCORE", "90.0"))
