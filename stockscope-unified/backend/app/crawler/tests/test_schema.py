"""
Tests for crawler_v2/schema/ modules.
"""

import json
import os
import tempfile

import pytest

from crawler_v2.schema.selector_store import SelectorStore
from crawler_v2.schema.schema_detector import SchemaDetector
from crawler_v2.schema.fallback_router import EmptyResult, FallbackRouter


# ---------------------------------------------------------------------------
# SelectorStore
# ---------------------------------------------------------------------------


class TestSelectorStore:
    def test_load_and_get(self, tmp_path):
        data = {
            "idx": {
                "company_profile": {
                    "company_name": "h1.name",
                    "sector": ".sector span",
                }
            }
        }
        path = tmp_path / "store.json"
        path.write_text(json.dumps(data))

        store = SelectorStore(str(path))
        selectors = store.get("idx", "company_profile")
        assert selectors["company_name"] == "h1.name"
        assert selectors["sector"] == ".sector span"

    def test_missing_file(self, tmp_path):
        store = SelectorStore(str(tmp_path / "nope.json"))
        assert store.get("idx", "profile") == {}

    def test_missing_source(self, tmp_path):
        path = tmp_path / "store.json"
        path.write_text("{}")
        store = SelectorStore(str(path))
        assert store.get("unknown", "type") == {}

    def test_get_sources(self, tmp_path):
        data = {"src_a": {}, "src_b": {}}
        path = tmp_path / "store.json"
        path.write_text(json.dumps(data))
        store = SelectorStore(str(path))
        assert set(store.get_sources()) == {"src_a", "src_b"}


# ---------------------------------------------------------------------------
# SchemaDetector
# ---------------------------------------------------------------------------


class TestSchemaDetector:
    def test_verify_found(self, tmp_path):
        data = {"test": {"page": {"title": "h1"}}}
        path = tmp_path / "store.json"
        path.write_text(json.dumps(data))
        store = SelectorStore(str(path))
        detector = SchemaDetector(store)

        html = "<html><body><h1>Hello</h1></body></html>"
        results = detector.verify_selectors(html, "test", "page")
        assert results["title"]["found"] is True
        assert results["title"]["value"] == "Hello"

    def test_verify_not_found(self, tmp_path):
        data = {"test": {"page": {"title": "h2.missing"}}}
        path = tmp_path / "store.json"
        path.write_text(json.dumps(data))
        store = SelectorStore(str(path))
        detector = SchemaDetector(store)

        html = "<html><body><h1>Hello</h1></body></html>"
        results = detector.verify_selectors(html, "test", "page")
        assert results["title"]["found"] is False

    def test_detect_changes_returns_failed(self, tmp_path):
        data = {"test": {"page": {"a": "h1", "b": ".missing"}}}
        path = tmp_path / "store.json"
        path.write_text(json.dumps(data))
        store = SelectorStore(str(path))
        detector = SchemaDetector(store)

        html = "<html><body><h1>Hi</h1></body></html>"
        failed = detector.detect_changes(html, "test", "page")
        assert "b" in failed
        assert "a" not in failed


# ---------------------------------------------------------------------------
# FallbackRouter
# ---------------------------------------------------------------------------


class TestFallbackRouter:
    @pytest.mark.asyncio
    async def test_returns_first_success(self):
        class GoodSource:
            async def fetch(self, ticker, session_mgr=None):
                result = type("R", (), {"has_data": lambda self: True, "source_name": ""})()
                return result

        class BadSource:
            async def fetch(self, ticker, session_mgr=None):
                raise RuntimeError("down")

        router = FallbackRouter(
            sources={"bad": BadSource(), "good": GoodSource()},
            chains={"profile": ["bad", "good"]},
        )
        result = await router.fetch_with_fallback("BBCA", "profile")
        assert result.source_name == "good"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_fail(self):
        class BadSource:
            async def fetch(self, ticker, session_mgr=None):
                raise RuntimeError("fail")

        router = FallbackRouter(
            sources={"s1": BadSource()},
            chains={"data": ["s1"]},
        )
        result = await router.fetch_with_fallback("BBCA", "data")
        assert isinstance(result, EmptyResult)
        assert result.has_data() is False

    @pytest.mark.asyncio
    async def test_empty_chain(self):
        router = FallbackRouter(sources={}, chains={"x": []})
        result = await router.fetch_with_fallback("T", "x")
        assert isinstance(result, EmptyResult)
