"""
crawler_v2/engine/session_manager.py — Manages aiohttp sessions with proxy
and header rotation.
"""

import aiohttp
from loguru import logger

from crawler_v2.anti_block.headers import get_headers
from crawler_v2.anti_block.proxy_manager import ProxyManager
from crawler_v2.anti_block.rate_limiter import polite_delay
from crawler_v2.config import MAX_RETRIES, PROXY_TIMEOUT


class SessionManager:
    """Wraps aiohttp.ClientSession with proxy rotation, retries, and polite delays."""

    def __init__(self, proxy_manager: ProxyManager):
        self.proxy_manager = proxy_manager
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=PROXY_TIMEOUT),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def fetch(self, url: str, retries: int = MAX_RETRIES) -> str | None:
        """Fetch *url* with automatic proxy rotation and retries.

        Returns the response body text, or ``None`` on exhausted retries.
        """
        for attempt in range(retries):
            proxy = await self.proxy_manager.get_proxy(url)
            headers = get_headers()
            try:
                await polite_delay()
                async with self._session.get(
                    url, proxy=proxy, headers=headers
                ) as resp:
                    if resp.status == 200:
                        if proxy:
                            await self.proxy_manager.report_success(proxy)
                        return await resp.text()
                    else:
                        logger.warning(
                            f"HTTP {resp.status} for {url} "
                            f"(attempt {attempt + 1}/{retries})"
                        )
                        if proxy:
                            await self.proxy_manager.report_failure(
                                proxy, blocked=(resp.status in (403, 429))
                            )
            except Exception as exc:
                logger.warning(
                    f"Request error for {url} "
                    f"(attempt {attempt + 1}/{retries}): {exc}"
                )
                if proxy:
                    await self.proxy_manager.report_failure(proxy)

        logger.error(f"All {retries} attempts failed for {url}")
        return None
