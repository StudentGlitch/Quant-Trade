"""
Tests for crawler_v2/anti_block/proxy_manager.py

Covers:
  - 4.3: Proxy health testing on startup
  - 4.4: Rotation modes, domain-hit limits, failure tracking
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crawler_v2.anti_block.proxy_manager import ProxyManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(proxies=None, mode="round_robin"):
    """Create a ProxyManager with explicit proxy list (skip file loading)."""
    mgr = ProxyManager(proxies=proxies or [], rotation_mode=mode)
    return mgr


# ---------------------------------------------------------------------------
# 4.3 — Health testing
# ---------------------------------------------------------------------------


class TestHealthTesting:
    """test_all_proxies and _test_proxy."""

    @pytest.mark.asyncio
    async def test_returns_only_working(self):
        mgr = _make_manager(["http://good:1", "http://bad:2", "http://good:3"])

        async def mock_test(proxy):
            return "good" in proxy

        mgr._test_proxy = mock_test
        working = await mgr.test_all_proxies()
        assert working == ["http://good:1", "http://good:3"]

    @pytest.mark.asyncio
    async def test_empty_proxy_list(self):
        mgr = _make_manager([])
        working = await mgr.test_all_proxies()
        assert working == []

    @pytest.mark.asyncio
    async def test_all_fail(self):
        mgr = _make_manager(["http://bad:1", "http://bad:2"])

        async def mock_test(proxy):
            return False

        mgr._test_proxy = mock_test
        working = await mgr.test_all_proxies()
        assert working == []

    @pytest.mark.asyncio
    async def test_exception_in_test_treated_as_false(self):
        mgr = _make_manager(["http://err:1", "http://good:2"])

        async def mock_test(proxy):
            if "err" in proxy:
                raise ConnectionError("boom")
            return True

        mgr._test_proxy = mock_test
        working = await mgr.test_all_proxies()
        # Exceptions are caught by gather(return_exceptions=True)
        # and compared with `is True` — so the errored proxy is excluded.
        assert working == ["http://good:2"]


# ---------------------------------------------------------------------------
# 4.4 — Rotation modes
# ---------------------------------------------------------------------------


class TestRoundRobin:
    @pytest.mark.asyncio
    async def test_cycles_through_proxies(self):
        mgr = _make_manager(["http://a:1", "http://b:2", "http://c:3"])
        mgr.working_proxies = mgr.proxies[:]

        first = await mgr.get_proxy("https://example.com")
        second = await mgr.get_proxy("https://example.com")
        third = await mgr.get_proxy("https://example.com")

        assert {first, second, third} == {"http://a:1", "http://b:2", "http://c:3"}

    @pytest.mark.asyncio
    async def test_returns_none_when_no_proxies(self):
        mgr = _make_manager([])
        assert await mgr.get_proxy("https://example.com") is None


class TestAdaptive:
    @pytest.mark.asyncio
    async def test_prefers_least_failed(self):
        mgr = _make_manager(
            ["http://a:1", "http://b:2"], mode="adaptive"
        )
        mgr.working_proxies = mgr.proxies[:]
        mgr._consecutive_failures["http://a:1"] = 2
        mgr._consecutive_failures["http://b:2"] = 0

        proxy = await mgr.get_proxy("https://example.com")
        assert proxy == "http://b:2"


# ---------------------------------------------------------------------------
# Domain-hit limiting
# ---------------------------------------------------------------------------


class TestDomainLimit:
    @pytest.mark.asyncio
    async def test_respects_domain_limit(self):
        mgr = _make_manager(["http://a:1"], mode="round_robin")
        mgr.working_proxies = mgr.proxies[:]

        # Fill up domain hits to the limit
        now = time.time()
        mgr._domain_hits["http://a:1"]["example.com"] = [now] * 10

        # Next call should still return the proxy (fallback behaviour)
        proxy = await mgr.get_proxy("https://example.com/page")
        assert proxy == "http://a:1"  # returned as last-resort fallback


# ---------------------------------------------------------------------------
# Failure tracking
# ---------------------------------------------------------------------------


class TestFailureTracking:
    @pytest.mark.asyncio
    async def test_proxy_marked_failed_after_threshold(self):
        mgr = _make_manager(["http://a:1", "http://b:2"])
        mgr.working_proxies = mgr.proxies[:]

        for _ in range(3):  # PROXY_FAIL_THRESHOLD default = 3
            await mgr.report_failure("http://a:1", blocked=True)

        assert "http://a:1" in mgr._failed_proxies

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        mgr = _make_manager(["http://a:1"])
        mgr.working_proxies = mgr.proxies[:]

        await mgr.report_failure("http://a:1")
        await mgr.report_failure("http://a:1")
        await mgr.report_success("http://a:1")
        await mgr.report_failure("http://a:1")

        # Should NOT be failed (reset by success)
        assert "http://a:1" not in mgr._failed_proxies

    @pytest.mark.asyncio
    async def test_stats(self):
        mgr = _make_manager(["http://a:1", "http://b:2"])
        mgr.working_proxies = mgr.proxies[:]

        await mgr.report_success("http://a:1")
        await mgr.report_failure("http://b:2")

        stats = mgr.get_stats()
        assert stats["total_proxies"] == 2
        assert stats["success_total"] == 1
        assert stats["fail_total"] == 1
