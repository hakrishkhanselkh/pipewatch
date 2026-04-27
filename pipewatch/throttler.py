"""Rate-limiting / throttling for metric result processing.

Allows callers to cap how many results are processed per source
within a rolling time window, dropping the excess.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Iterable, List

from pipewatch.metrics import MetricResult


@dataclass
class ThrottleConfig:
    """Configuration for the throttler."""
    max_per_window: int = 10
    window_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_per_window < 1:
            raise ValueError("max_per_window must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")


class Throttler:
    """Drop results that exceed a per-source rate limit.

    Parameters
    ----------
    config:
        Throttling parameters shared across all sources.
    """

    def __init__(self, config: ThrottleConfig | None = None) -> None:
        self._config = config or ThrottleConfig()
        # source -> deque of timestamps (floats) within the current window
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._dropped: dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter(self, results: Iterable[MetricResult]) -> List[MetricResult]:
        """Return only those results that are within the rate limit."""
        allowed: List[MetricResult] = []
        for result in results:
            if self._allow(result.source, time.monotonic()):
                allowed.append(result)
            else:
                self._dropped[result.source] += 1
        return allowed

    def dropped_count(self, source: str) -> int:
        """Total results dropped for *source* since creation."""
        return self._dropped[source]

    def reset(self, source: str | None = None) -> None:
        """Clear state for *source*, or all sources when *source* is None."""
        if source is None:
            self._windows.clear()
            self._dropped.clear()
        else:
            self._windows.pop(source, None)
            self._dropped.pop(source, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _allow(self, source: str, now: float) -> bool:
        window = self._windows[source]
        cutoff = now - self._config.window_seconds
        # Evict timestamps outside the rolling window
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) < self._config.max_per_window:
            window.append(now)
            return True
        return False
