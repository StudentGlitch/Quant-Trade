"""
crawler_v2/anti_block/proxy_manager.py — Proxy health testing on startup
and rotation with domain-aware rate limiting.

Implements:
  - 4.3: Proxy health testing on startup (test_all_proxies / _test_proxy)
  - 4.4: Proxy rotation trigger rules (round_robin / adaptive),
          domain-hit tracking, consecutive-failure tracking,
          and Redis-compatible performance logging.
"""

import asyncio
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from loguru import logger

from crawler_v2.config import (
    PROXY_FAIL_THRESHOLD,
    PROXY_FILE,
    PROXY_MAX_DOMAIN_HITS,
    PROXY_ROTATION_MODE,
    PROXY_TEST_URL,
    PROXY_TIMEOUT,
)


class ProxyManager:
    """Manages a pool of proxies with health testing and smart rotation."""

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        rotation_mode: Optional[str] = None,
        redis_client=None,
    ):
        self.proxies: List[str] = proxies or self._load_proxies()
        self.working_proxies: List[str] = []
        self.rotation_mode: str = rotation_mode or PROXY_ROTATION_MODE
        self.redis = redis_client

        # Round-robin index
        self._rr_index: int = 0
        self._lock = asyncio.Lock()

        # Domain-hit tracking: {proxy: {domain: [(timestamp, ...)]}}
        self._domain_hits: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Consecutive failure tracking: {proxy: consecutive_fail_count}
        self._consecutive_failures: Dict[str, int] = defaultdict(int)

        # Failed proxies (removed from rotation)
        self._failed_proxies: set = set()

        # Performance counters
        self._success_count: Dict[str, int] = defaultdict(int)
        self._fail_count: Dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Proxy file loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_proxies() -> List[str]:
        """Load proxies from the configured file (one per line)."""
        proxy_file = PROXY_FILE
        if not os.path.isfile(proxy_file):
            logger.warning(f"Proxy file not found: {proxy_file}")
            return []
        with open(proxy_file) as fh:
            proxies = [
                line.strip()
                for line in fh
                if line.strip() and not line.startswith("#")
            ]
        logger.info(f"Loaded {len(proxies)} proxies from {proxy_file}")
        return proxies

    # ------------------------------------------------------------------
    # 4.3 — Proxy health testing on startup
    # ------------------------------------------------------------------

    async def test_all_proxies(self) -> List[str]:
        """Test all proxies concurrently and return only the working ones."""
        if not self.proxies:
            logger.info("No proxies configured — running without proxy pool")
            return []

        results = await asyncio.gather(
            *[self._test_proxy(p) for p in self.proxies],
            return_exceptions=True,
        )

        working = [
            p for p, r in zip(self.proxies, results) if r is True
        ]
        logger.info(
            f"Proxies: {len(working)}/{len(self.proxies)} working"
        )
        self.working_proxies = working
        return working

    async def _test_proxy(self, proxy: str) -> bool:
        """Test a single proxy by making a request to the test URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    PROXY_TEST_URL,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(
                        total=PROXY_TIMEOUT
                    ),
                ) as response:
                    return response.status == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 4.4 — Proxy rotation
    # ------------------------------------------------------------------

    async def get_proxy(self, url: str) -> Optional[str]:
        """Return the next proxy for *url* based on rotation mode.

        Returns ``None`` if no proxies are available.
        """
        if not self.working_proxies:
            return None

        domain = urlparse(url).netloc

        if self.rotation_mode == "round_robin":
            return await self._round_robin(domain)
        elif self.rotation_mode == "adaptive":
            return await self._adaptive(domain)
        return await self._round_robin(domain)

    async def _round_robin(self, domain: str) -> Optional[str]:
        """Simple round-robin rotation with domain-hit guard."""
        async with self._lock:
            available = [
                p for p in self.working_proxies
                if p not in self._failed_proxies
            ]
            if not available:
                return None

            start_index = self._rr_index % len(available)
            self._rr_index += 1

            # Try starting from the round-robin position
            for offset in range(len(available)):
                idx = (start_index + offset) % len(available)
                proxy = available[idx]
                if self._check_domain_limit(proxy, domain):
                    self._record_domain_hit(proxy, domain)
                    return proxy

            # All proxies exceeded domain limit — return the round-robin pick
            proxy = available[start_index]
            self._record_domain_hit(proxy, domain)
            return proxy

    async def _adaptive(self, domain: str) -> Optional[str]:
        """Rotate only on block detection — pick the least-failed proxy."""
        async with self._lock:
            available = [
                p for p in self.working_proxies
                if p not in self._failed_proxies
            ]
            if not available:
                return None

            # Prefer proxies with fewer failures and within domain limit
            candidates = [
                p for p in available
                if self._check_domain_limit(p, domain)
            ]
            if not candidates:
                candidates = available

            # Sort by failure count (ascending)
            candidates.sort(key=lambda p: self._consecutive_failures[p])
            proxy = candidates[0]
            self._record_domain_hit(proxy, domain)
            return proxy

    # ------------------------------------------------------------------
    # Domain-hit tracking
    # ------------------------------------------------------------------

    def _check_domain_limit(self, proxy: str, domain: str) -> bool:
        """Return True if *proxy* has not exceeded the per-domain hit limit
        within the last 60 seconds."""
        now = time.time()
        hits = self._domain_hits[proxy][domain]
        # Prune old hits (> 60s)
        recent = [t for t in hits if now - t < 60]
        self._domain_hits[proxy][domain] = recent
        return len(recent) < PROXY_MAX_DOMAIN_HITS

    def _record_domain_hit(self, proxy: str, domain: str) -> None:
        """Record a hit for proxy+domain."""
        self._domain_hits[proxy][domain].append(time.time())

    # ------------------------------------------------------------------
    # Success / failure reporting
    # ------------------------------------------------------------------

    async def report_success(self, proxy: str) -> None:
        """Mark a successful request for *proxy*."""
        self._consecutive_failures[proxy] = 0
        self._success_count[proxy] += 1
        await self._log_to_redis(proxy, "success")

    async def report_failure(self, proxy: str, blocked: bool = False) -> None:
        """Mark a failed/blocked request for *proxy*.

        After PROXY_FAIL_THRESHOLD consecutive failures on ANY domain,
        the proxy is removed from the active pool.
        """
        self._consecutive_failures[proxy] += 1
        self._fail_count[proxy] += 1
        await self._log_to_redis(proxy, "fail")

        if self._consecutive_failures[proxy] >= PROXY_FAIL_THRESHOLD:
            self._failed_proxies.add(proxy)
            logger.warning(
                f"Proxy marked as failed after "
                f"{PROXY_FAIL_THRESHOLD} consecutive blocks: {proxy}"
            )

    async def _log_to_redis(self, proxy: str, result: str) -> None:
        """Log proxy performance to Redis if available."""
        if self.redis is None:
            return
        try:
            ip = urlparse(proxy).hostname or proxy
            key = f"proxy:{ip}:{result}"
            await self.redis.incr(key)
        except Exception as exc:
            logger.debug(f"Redis log failed for {proxy}: {exc}")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return a summary of proxy pool health."""
        total = len(self.proxies)
        healthy = len([
            p for p in self.working_proxies
            if p not in self._failed_proxies
        ])
        return {
            "total_proxies": total,
            "healthy_proxies": healthy,
            "failed_proxies": len(self._failed_proxies),
            "success_total": sum(self._success_count.values()),
            "fail_total": sum(self._fail_count.values()),
        }
