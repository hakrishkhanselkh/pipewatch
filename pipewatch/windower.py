"""Sliding-window aggregation over MetricResult streams."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Deque, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class WindowStats:
    source: str
    name: str
    window_seconds: float
    count: int
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    critical_count: int
    warning_count: int
    ok_count: int

    def __str__(self) -> str:
        return (
            f"[{self.source}/{self.name}] "
            f"window={self.window_seconds}s count={self.count} "
            f"avg={self.avg_value:.3f} "
            f"ok={self.ok_count} warn={self.warning_count} crit={self.critical_count}"
        ) if self.avg_value is not None else (
            f"[{self.source}/{self.name}] window={self.window_seconds}s count=0"
        )


@dataclass
class WindowConfig:
    window_seconds: float = 60.0
    max_entries: int = 1000

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")


class ResultWindower:
    """Maintains a sliding time window of MetricResults per (source, name) key."""

    def __init__(self, config: Optional[WindowConfig] = None) -> None:
        self._config = config or WindowConfig()
        self._buckets: dict[tuple[str, str], Deque[MetricResult]] = {}

    def add(self, result: MetricResult) -> None:
        key = (result.metric.source, result.metric.name)
        if key not in self._buckets:
            self._buckets[key] = deque(maxlen=self._config.max_entries)
        self._buckets[key].append(result)
        self._evict(key)

    def _evict(self, key: tuple[str, str]) -> None:
        cutoff = datetime.utcnow() - timedelta(seconds=self._config.window_seconds)
        bucket = self._buckets[key]
        while bucket and bucket[0].timestamp is not None and bucket[0].timestamp < cutoff:
            bucket.popleft()

    def stats(self, source: str, name: str) -> WindowStats:
        key = (source, name)
        self._evict(key) if key in self._buckets else None
        entries: List[MetricResult] = list(self._buckets.get(key, []))
        values = [r.value for r in entries if r.value is not None]
        return WindowStats(
            source=source,
            name=name,
            window_seconds=self._config.window_seconds,
            count=len(entries),
            min_value=min(values) if values else None,
            max_value=max(values) if values else None,
            avg_value=sum(values) / len(values) if values else None,
            critical_count=sum(1 for r in entries if r.status == MetricStatus.CRITICAL),
            warning_count=sum(1 for r in entries if r.status == MetricStatus.WARNING),
            ok_count=sum(1 for r in entries if r.status == MetricStatus.OK),
        )

    def all_stats(self) -> List[WindowStats]:
        return [self.stats(src, name) for src, name in list(self._buckets.keys())]

    def clear(self) -> None:
        self._buckets.clear()
