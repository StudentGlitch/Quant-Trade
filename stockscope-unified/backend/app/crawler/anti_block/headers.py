"""
crawler_v2/anti_block/headers.py — Rotating User-Agent and request headers.
"""

import random
from typing import Dict

from loguru import logger

_UA_POOL: list = []


def _init_ua_pool() -> list:
    """Build or return a cached pool of realistic User-Agent strings."""
    global _UA_POOL
    if _UA_POOL:
        return _UA_POOL
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        _UA_POOL = [ua.random for _ in range(20)]
    except Exception:
        logger.debug("fake_useragent unavailable — using fallback UA pool")
        _UA_POOL = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        ]
    return _UA_POOL


def get_headers() -> Dict[str, str]:
    """Return realistic HTTP headers with a random User-Agent."""
    pool = _init_ua_pool()
    return {
        "User-Agent": random.choice(pool),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
    }
