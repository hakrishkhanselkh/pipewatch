"""Deduplicator: suppress repeated identical MetricResults within a time window."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from pipewatch.metrics import MetricResult


def _result_fingerprint(result: MetricResult) -> str:
    """Return a stable hash representing the identity + status of a result."""
    key = f"{result.metric.source}::{result.metric.name}::{result.status.value}::{result.value}"
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class _Entry:
    fingerprint: str
    first_seen: float
    last_seen: float
    count: int = 1


class Deduplicator:
    """Filter out duplicate MetricResults seen within *window_seconds*.

    A result is considered a duplicate when its source, name, status, and value
    are identical to a previously seen result within the deduplication window.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.window_seconds = window_seconds
        self._cache: Dict[str, _Entry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_duplicate(self, result: MetricResult, *, _now: Optional[float] = None) -> bool:
        """Return True if *result* is a duplicate within the current window."""
        now = _now if _now is not None else time.monotonic()
        fp = _result_fingerprint(result)
        entry = self._cache.get(fp)

        if entry is None or (now - entry.first_seen) > self.window_seconds:
            self._cache[fp] = _Entry(fingerprint=fp, first_seen=now, last_seen=now)
            return False

        entry.last_seen = now
        entry.count += 1
        return True

    def filter(self, results: list[MetricResult], *, _now: Optional[float] = None) -> list[MetricResult]:
        """Return only the non-duplicate results from *results*."""
        now = _now if _now is not None else time.monotonic()
        return [r for r in results if not self.is_duplicate(r, _now=now)]

    def reset(self) -> None:
        """Clear all cached fingerprints."""
        self._cache.clear()

    def stats(self) -> Dict[str, int]:
        """Return a mapping of fingerprint -> seen count for diagnostics."""
        return {fp: entry.count for fp, entry in self._cache.items()}

    def __len__(self) -> int:
        return len(self._cache)
