"""Metric result history store with trend detection."""

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class TrendInfo:
    """Describes the recent trend for a single metric."""

    source: str
    name: str
    window: int
    values: List[float]
    direction: str  # 'rising', 'falling', 'stable'
    last_status: Optional[MetricStatus] = None

    def __str__(self) -> str:
        return (
            f"[{self.source}/{self.name}] trend={self.direction} "
            f"over last {self.window} samples, "
            f"values={[round(v, 3) for v in self.values]}"
        )


class MetricHistory:
    """Stores a rolling window of MetricResults and exposes trend helpers."""

    def __init__(self, maxlen: int = 20) -> None:
        if maxlen < 2:
            raise ValueError("maxlen must be >= 2")
        self._maxlen = maxlen
        # key: (source, name) -> deque of MetricResult
        self._store: Dict[tuple, Deque[MetricResult]] = {}

    # ------------------------------------------------------------------
    def record(self, result: MetricResult) -> None:
        """Append a result to its rolling window."""
        key = (result.metric.source, result.metric.name)
        if key not in self._store:
            self._store[key] = deque(maxlen=self._maxlen)
        self._store[key].append(result)

    def record_all(self, results: List[MetricResult]) -> None:
        for r in results:
            self.record(r)

    # ------------------------------------------------------------------
    def get(self, source: str, name: str) -> List[MetricResult]:
        """Return stored results for a metric (oldest first)."""
        return list(self._store.get((source, name), []))

    def trend(self, source: str, name: str, window: int = 5) -> Optional[TrendInfo]:
        """Return trend info for the last *window* samples, or None if insufficient data."""
        results = self.get(source, name)
        if len(results) < 2:
            return None
        recent = results[-window:]
        values = [r.value for r in recent]
        direction = _detect_direction(values)
        return TrendInfo(
            source=source,
            name=name,
            window=len(recent),
            values=values,
            direction=direction,
            last_status=recent[-1].status,
        )

    def all_trends(self, window: int = 5) -> List[TrendInfo]:
        """Return trend info for every tracked metric."""
        trends = []
        for source, name in self._store:
            t = self.trend(source, name, window=window)
            if t is not None:
                trends.append(t)
        return trends

    def __len__(self) -> int:
        return sum(len(v) for v in self._store.values())


# ---------------------------------------------------------------------------
def _detect_direction(values: List[float], tolerance: float = 0.01) -> str:
    """Classify a value sequence as rising, falling, or stable."""
    if len(values) < 2:
        return "stable"
    delta = values[-1] - values[0]
    span = max(abs(v) for v in values) or 1.0
    ratio = delta / span
    if ratio > tolerance:
        return "rising"
    if ratio < -tolerance:
        return "falling"
    return "stable"
