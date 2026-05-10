"""
crawler_v2/main.py — Entry point for the advanced async crawler v2.

Supports the same CLI arguments as the v1 crawler:
  python crawler_v2/main.py --all
  python crawler_v2/main.py --ticker BBCA
  python crawler_v2/main.py --gap-fill
  python crawler_v2/main.py --resume
"""

import argparse
import asyncio
import ast
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from loguru import logger

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from crawler_v2.config import CRAWLER_V2_CONCURRENCY
from crawler_v2.anti_block.proxy_manager import ProxyManager
from crawler_v2.engine.async_engine import AsyncCrawlEngine
from crawler_v2.gap.gap_detector import GapDetector
from crawler_v2.gap.gap_queue import GapQueue
from crawler_v2.schema.fallback_router import FallbackRouter
from crawler_v2.utils.logger import setup_logger


IDX_STOCK_LIST_URL = (
    "https://www.idx.co.id/primary/ListedCompany/GetStockList"
    "?start=0&length=9999&sectorCode=&subsectorCode=&industryCode="
    "&boardCode=&searchTicker="
)
MIN_ALL_TICKERS = int(os.getenv("CRAWLER_V2_MIN_ALL_TICKERS", "900"))
ALLOW_PARTIAL_ALL = os.getenv("CRAWLER_V2_ALLOW_PARTIAL_ALL", "false").lower() in {
    "1",
    "true",
    "yes",
}
TICKER_SNAPSHOT_PATH = Path(
    os.getenv(
        "CRAWLER_V2_TICKER_SNAPSHOT_PATH",
        str(Path(__file__).resolve().parent / "ticker_snapshot.json"),
    )
)


def _idx_headers() -> dict:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.idx.co.id/",
        "Connection": "keep-alive",
    }


def _normalize_tickers(raw_tickers: list[str]) -> list[str]:
    return sorted({str(t).strip().upper() for t in raw_tickers if str(t).strip()})


def _is_strong_universe(tickers: list[str], min_tickers: int = MIN_ALL_TICKERS) -> bool:
    return len(set(tickers)) >= min_tickers


def _save_ticker_snapshot(tickers: list[str], source: str) -> None:
    payload = {
        "source": source,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(tickers),
        "tickers": tickers,
    }
    try:
        TICKER_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TICKER_SNAPSHOT_PATH.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning(f"Could not save ticker snapshot: {exc}")


def _load_tickers_from_snapshot() -> list[str]:
    if not TICKER_SNAPSHOT_PATH.exists():
        return []

    try:
        payload = json.loads(TICKER_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    tickers = payload.get("tickers", []) if isinstance(payload, dict) else []
    return _normalize_tickers(tickers)


def _load_fallback_tickers() -> list[str]:
    """Load TARGET_TICKERS from apps/api/scripts/config.py as a local fallback."""
    fallback_path = (
        Path(__file__).resolve().parents[2] / "apps" / "api" / "scripts" / "config.py"
    )
    if not fallback_path.exists():
        return []

    try:
        raw = fallback_path.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        module = ast.parse(raw)
    except SyntaxError:
        return []

    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TARGET_TICKERS":
                    try:
                        tickers = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError):
                        return []
                    return _normalize_tickers(tickers)
    return []


def _load_tickers_from_database() -> list[str]:
    """Load tickers from the companies table when DATABASE_URL is available."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        env_path = Path(__file__).resolve().parents[1] / "jkse-crawler" / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() == "DATABASE_URL":
                        database_url = value.strip().strip('"').strip("'")
                        break
            except OSError:
                return []

    if not database_url:
        return []

    try:
        from sqlalchemy import create_engine, text
    except Exception:
        return []

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT ticker
                    FROM companies
                    WHERE ticker IS NOT NULL AND ticker <> ''
                    """
                )
            )
            tickers = _normalize_tickers([row[0] for row in rows if row[0]])
            return tickers
    except Exception as exc:
        logger.warning(f"Database ticker fallback failed: {exc}")
        return []


async def fetch_all_idx_tickers() -> list[str]:
    """Fetch all IDX-listed tickers from the public IDX stock list endpoint."""
    timeout = aiohttp.ClientTimeout(total=30)
    idx_tickers: list[str] = []
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=_idx_headers()) as session:
            async with session.get(IDX_STOCK_LIST_URL) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        records = payload.get("data", []) if isinstance(payload, dict) else []
        idx_tickers = _normalize_tickers(
            [record.get("StockCode", "") for record in records if record.get("StockCode")]
        )
        if _is_strong_universe(idx_tickers):
            _save_ticker_snapshot(idx_tickers, "idx_api")
            return idx_tickers
        if idx_tickers:
            logger.warning(
                f"IDX ticker fetch returned only {len(idx_tickers)} tickers "
                f"(< {MIN_ALL_TICKERS}); trying stronger fallbacks"
            )
    except Exception as exc:
        logger.warning(f"IDX ticker fetch failed: {exc}")

    db_fallback = _load_tickers_from_database()
    if _is_strong_universe(db_fallback):
        logger.warning(f"Falling back to companies table with {len(db_fallback)} tickers")
        _save_ticker_snapshot(db_fallback, "companies_table")
        return db_fallback

    snapshot_fallback = _load_tickers_from_snapshot()
    if _is_strong_universe(snapshot_fallback):
        logger.warning(
            f"Falling back to ticker snapshot with {len(snapshot_fallback)} tickers"
        )
        return snapshot_fallback

    config_fallback = _load_fallback_tickers()
    if _is_strong_universe(config_fallback):
        logger.warning(
            f"Falling back to apps/api/scripts/config.py with {len(config_fallback)} tickers"
        )
        return config_fallback

    # Return the largest available list so caller can decide whether to fail or continue.
    candidates = [idx_tickers, db_fallback, snapshot_fallback, config_fallback]
    best = max(candidates, key=len, default=[])
    if best:
        logger.warning(
            f"No fallback reached {MIN_ALL_TICKERS} tickers; best available is {len(best)}"
        )
    return best


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="JKSE Advanced Async Crawler v2"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Crawl all ~900 JKSE companies"
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        help="Crawl a single ticker (e.g. BBCA)"
    )
    parser.add_argument(
        "--gap-fill", action="store_true",
        help="Run gap detection and filling only"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint"
    )
    parser.add_argument(
        "--workers", type=int,
        default=int(os.getenv("CRAWLER_V2_CONCURRENCY",
                              str(CRAWLER_V2_CONCURRENCY))),
        help="Number of async workers"
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    setup_logger()

    logger.info("=== JKSE Crawler v2 starting ===")
    logger.info(f"Workers: {args.workers}")
    start = time.time()

    # --- Proxy setup ---
    proxy_mgr = ProxyManager()
    await proxy_mgr.test_all_proxies()

    # --- Fallback router (sources registered here in production) ---
    router = FallbackRouter()

    # --- Engine ---
    engine = AsyncCrawlEngine(
        proxy_manager=proxy_mgr,
        fallback_router=router,
        workers=args.workers,
    )

    # --- Determine tickers ---
    if args.ticker:
        tickers = [args.ticker.upper()]
    elif args.all:
        tickers = await fetch_all_idx_tickers()
        logger.info(f"--all mode loaded {len(tickers)} tickers")
        if not _is_strong_universe(tickers):
            message = (
                f"--all mode requires >= {MIN_ALL_TICKERS} tickers but resolved {len(tickers)}. "
                "Populate companies table, refresh snapshot, or set "
                "CRAWLER_V2_ALLOW_PARTIAL_ALL=true to override."
            )
            if ALLOW_PARTIAL_ALL:
                logger.warning(message)
            else:
                logger.error(message)
                raise SystemExit(2)
    else:
        tickers = []

    # --- Gap fill mode ---
    if args.gap_fill:
        logger.info("Running gap-fill only")
        detector = GapDetector()
        gaps = detector.detect_gaps()
        queue = GapQueue()
        await queue.load_gaps(gaps)
        processed = await queue.process(engine)
        logger.info(f"Gap fill complete: {processed} gaps processed")
    elif tickers:
        logger.info(f"Crawling {len(tickers)} tickers")
        results = await engine.crawl_all(tickers)
        logger.info(f"Results: {len(results)} items")
    else:
        logger.warning(
            "No action specified. Use --all, --ticker, --gap-fill, or --resume"
        )

    elapsed = time.time() - start
    logger.info(f"=== Crawler v2 finished in {elapsed:.1f}s ===")


if __name__ == "__main__":
    asyncio.run(main())
