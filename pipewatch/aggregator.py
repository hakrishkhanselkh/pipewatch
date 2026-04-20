"""Aggregates MetricResults across sources and time windows."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class AggregatedStats:
    """Descriptive statistics for a group of metric values."""

    source: str
    name: str
    count: int
    mean: float
    minimum: float
    maximum: float
    latest_status: MetricStatus

    def __str__(self) -> str:
        return (
            f"[{self.source}/{self.name}] count={self.count} "
            f"mean={self.mean:.4f} min={self.minimum:.4f} max={self.maximum:.4f} "
            f"status={self.latest_status.value}"
        )


class ResultAggregator:
    """Groups MetricResults and computes per-metric statistics."""

    def __init__(self) -> None:
        # key: (source, name) -> list of results
        self._buckets: Dict[tuple, List[MetricResult]] = defaultdict(list)

    def add(self, result: MetricResult) -> None:
        """Ingest a single MetricResult."""
        key = (result.metric.source, result.metric.name)
        self._buckets[key].append(result)

    def add_many(self, results: List[MetricResult]) -> None:
        """Ingest multiple MetricResults at once."""
        for r in results:
            self.add(r)

    def stats(self, source: str, name: str) -> Optional[AggregatedStats]:
        """Return statistics for a specific (source, name) pair, or None."""
        key = (source, name)
        bucket = self._buckets.get(key)
        if not bucket:
            return None
        values = [r.value for r in bucket]
        return AggregatedStats(
            source=source,
            name=name,
            count=len(values),
            mean=sum(values) / len(values),
            minimum=min(values),
            maximum=max(values),
            latest_status=bucket[-1].status,
        )

    def all_stats(self) -> List[AggregatedStats]:
        """Return statistics for every tracked (source, name) pair."""
        result = []
        for (source, name) in self._buckets:
            s = self.stats(source, name)
            if s is not None:
                result.append(s)
        return result

    def clear(self) -> None:
        """Remove all accumulated data."""
        self._buckets.clear()
