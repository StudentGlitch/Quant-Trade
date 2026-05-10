"""
crawler_v2/engine/async_engine.py — Core async crawl orchestrator.

Manages concurrent workers, dispatches tickers to crawl tasks,
and coordinates the overall crawl lifecycle.
"""

import asyncio
import time
from typing import List, Optional

from loguru import logger

from crawler_v2.anti_block.proxy_manager import ProxyManager
from crawler_v2.config import CRAWLER_V2_CONCURRENCY
from crawler_v2.engine.session_manager import SessionManager
from crawler_v2.schema.fallback_router import FallbackRouter


class AsyncCrawlEngine:
    """Orchestrates concurrent crawling of multiple tickers."""

    def __init__(
        self,
        proxy_manager: ProxyManager,
        fallback_router: FallbackRouter,
        workers: int = CRAWLER_V2_CONCURRENCY,
        iteration: int = 1,
    ):
        self.proxy_manager = proxy_manager
        self.fallback_router = fallback_router
        self.workers = workers
        self.iteration = iteration

        self._queue: asyncio.Queue = asyncio.Queue()
        self._results: list = []
        self._start_time: float = 0

    async def crawl_all(
        self,
        tickers: List[str],
        data_types: Optional[List[str]] = None,
    ) -> List[dict]:
        """Crawl all *tickers* concurrently with worker pool."""
        data_types = data_types or [
            "company_profile",
            "financials",
            "stock_prices",
            "executives",
            "news",
            "esg",
        ]

        self._start_time = time.time()
        self._results = []

        # Enqueue work items
        for ticker in tickers:
            for dt in data_types:
                await self._queue.put((ticker, dt))

        logger.info(
            f"Starting crawl: {len(tickers)} tickers × "
            f"{len(data_types)} types = {self._queue.qsize()} tasks "
            f"({self.workers} workers)"
        )

        # Launch worker pool
        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.workers)
        ]

        # Wait for all tasks to complete
        await self._queue.join()

        # Cancel workers
        for w in workers:
            w.cancel()

        elapsed = time.time() - self._start_time
        logger.info(
            f"Crawl complete: {len(self._results)} results "
            f"in {elapsed:.1f}s"
        )
        return self._results

    async def crawl_specific(
        self,
        ticker: str,
        data_types: Optional[List[str]] = None,
    ) -> List[dict]:
        """Crawl a single ticker for specific data types."""
        return await self.crawl_all([ticker], data_types)

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that pulls tasks from the queue."""
        async with SessionManager(self.proxy_manager) as session_mgr:
            while True:
                try:
                    ticker, data_type = await self._queue.get()
                except asyncio.CancelledError:
                    return
                try:
                    result = await self.fallback_router.fetch_with_fallback(
                        ticker, data_type, session_mgr
                    )
                    self._results.append({
                        "ticker": ticker,
                        "data_type": data_type,
                        "result": result,
                        "worker": worker_id,
                    })
                except Exception as exc:
                    logger.error(
                        f"Worker {worker_id} error for "
                        f"{ticker}/{data_type}: {exc}"
                    )
                    self._results.append({
                        "ticker": ticker,
                        "data_type": data_type,
                        "result": None,
                        "error": str(exc),
                        "worker": worker_id,
                    })
                finally:
                    self._queue.task_done()
