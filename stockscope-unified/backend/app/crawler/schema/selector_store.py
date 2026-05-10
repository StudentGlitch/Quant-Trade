"""
crawler_v2/schema/selector_store.py — Load / query CSS selectors from JSON.

Selectors are stored in ``selector_store.json`` and keyed by
source → data_type → field → CSS selector string.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from crawler_v2.config import SELECTOR_STORE_PATH


class SelectorStore:
    """Read-only accessor for the selector JSON file."""

    def __init__(self, path: Optional[str] = None):
        self._path = Path(path or SELECTOR_STORE_PATH)
        self._data: Dict = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            logger.warning(f"Selector store not found: {self._path}")
            return
        with open(self._path) as fh:
            self._data = json.load(fh)
        logger.info(f"Selector store loaded: {list(self._data.keys())}")

    def get(self, source_name: str, data_type: str) -> Dict[str, str]:
        """Return ``{field: selector}`` for the given source/data_type,
        or an empty dict if not found."""
        return self._data.get(source_name, {}).get(data_type, {})

    def get_sources(self) -> list:
        """Return all source names."""
        return list(self._data.keys())

    def reload(self) -> None:
        """Re-read the JSON file from disk."""
        self._load()
