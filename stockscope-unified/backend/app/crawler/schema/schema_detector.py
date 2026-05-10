"""
crawler_v2/schema/schema_detector.py — Detects when a site changes its
HTML structure so selectors break.

Uses selectolax for fast CSS matching.  When selectors fail, logs to the
``selector_failures`` table and emits a warning.
"""

from typing import Dict, Optional

from loguru import logger

from crawler_v2.schema.selector_store import SelectorStore


class SchemaDetector:
    """Verifies CSS selectors against HTML and detects structural changes."""

    def __init__(self, selector_store: SelectorStore):
        self.store = selector_store

    def verify_selectors(
        self,
        html: str,
        source_name: str,
        data_type: str,
    ) -> Dict[str, dict]:
        """Check every selector for *source_name/data_type* against *html*.

        Returns ``{field: {found, selector, value}}`` for every field.
        """
        selectors = self.store.get(source_name, data_type)
        results: Dict[str, dict] = {}

        try:
            from selectolax.parser import HTMLParser
            tree = HTMLParser(html)
        except Exception as exc:
            for field in selectors:
                results[field] = {"found": False, "error": str(exc)}
            return results

        for field, selector in selectors.items():
            try:
                node = tree.css_first(selector)
                results[field] = {
                    "found": node is not None,
                    "selector": selector,
                    "value": node.text() if node else None,
                }
            except Exception as exc:
                results[field] = {
                    "found": False,
                    "error": str(exc),
                }
        return results

    def detect_changes(
        self,
        html: str,
        source_name: str,
        data_type: str,
        sample_url: Optional[str] = None,
    ) -> Dict[str, dict]:
        """Run selector verification and return only the *failed* fields.

        Logs a warning and triggers an alert when failures are detected.
        """
        results = self.verify_selectors(html, source_name, data_type)
        failed = {f: r for f, r in results.items() if not r["found"]}

        if failed:
            logger.warning(
                f"Schema change detected: {source_name}/{data_type} — "
                f"missing: {list(failed.keys())}"
            )
            self._alert_schema_change(
                source_name, data_type, failed, sample_url
            )
        return failed

    @staticmethod
    def _alert_schema_change(
        source_name: str,
        data_type: str,
        failed: dict,
        sample_url: Optional[str] = None,
    ) -> None:
        """Log schema failure for manual review.

        In production this would write to the selector_failures DB table
        and send a notification.
        """
        logger.error(
            f"ALERT: Selector failure — {source_name}/{data_type} "
            f"fields={list(failed.keys())} url={sample_url}"
        )
