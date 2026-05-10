"""
crawler_v2/anti_block/rate_limiter.py — Async-aware rate limiter for the v2 crawler.
"""

import asyncio
import random

from crawler_v2.config import CRAWL_DELAY_MIN, CRAWL_DELAY_MAX


async def polite_delay() -> None:
    """Async sleep for a random interval between configured min/max."""
    delay = random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX)
    await asyncio.sleep(delay)


async def handle_rate_limit(status_code: int) -> float:
    """Handle rate-limiting responses.  Returns the wait duration in seconds."""
    if status_code == 429:
        wait = random.uniform(30, 60)
    elif status_code == 403:
        wait = random.uniform(10, 30)
    elif status_code >= 500:
        wait = random.uniform(5, 15)
    else:
        wait = 0
    if wait:
        await asyncio.sleep(wait)
    return wait


async def exponential_backoff(attempt: int, base: float = 2.0, cap: float = 30.0) -> float:
    """Async exponential backoff: 2^attempt capped at *cap* seconds."""
    delay = min(base ** attempt, cap)
    await asyncio.sleep(delay)
    return delay
