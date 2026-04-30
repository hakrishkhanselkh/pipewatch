"""Merge multiple lists of MetricResults into a single deduplicated collection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


def _default_key(result: MetricResult) -> tuple:
    """Identity key: (source, metric name)."""
    return (result.metric.source, result.metric.name)


@dataclass
class MergeReport:
    """Summary produced by a merge operation."""

    results: List[MetricResult] = field(default_factory=list)
    duplicate_count: int = 0
    source_count: int = 0

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"MergeReport(total={len(self.results)}, "
            f"duplicates_dropped={self.duplicate_count}, "
            f"sources={self.source_count})"
        )


class ResultMerger:
    """Merge result streams, resolving conflicts by a configurable strategy.

    Conflict strategies
    -------------------
    ``'worst'``  – keep the result with the highest severity (default).
    ``'first'``  – keep the first result seen.
    ``'last'``   – keep the last result seen.
    """

    _STATUS_RANK = {
        MetricStatus.OK: 0,
        MetricStatus.WARNING: 1,
        MetricStatus.CRITICAL: 2,
    }

    def __init__(
        self,
        strategy: str = "worst",
        key_fn: Optional[Callable[[MetricResult], tuple]] = None,
    ) -> None:
        if strategy not in ("worst", "first", "last"):
            raise ValueError(f"Unknown strategy {strategy!r}; choose worst/first/last")
        self._strategy = strategy
        self._key_fn: Callable[[MetricResult], tuple] = key_fn or _default_key

    # ------------------------------------------------------------------
    def merge(self, *streams: Iterable[MetricResult]) -> MergeReport:
        """Merge one or more iterables of MetricResult into a single report."""
        seen: dict[tuple, MetricResult] = {}
        duplicate_count = 0
        sources: set[str] = set()

        for stream in streams:
            for result in stream:
                sources.add(result.metric.source)
                key = self._key_fn(result)
                if key not in seen:
                    seen[key] = result
                else:
                    duplicate_count += 1
                    seen[key] = self._resolve(seen[key], result)

        return MergeReport(
            results=list(seen.values()),
            duplicate_count=duplicate_count,
            source_count=len(sources),
        )

    # ------------------------------------------------------------------
    def _resolve(self, existing: MetricResult, incoming: MetricResult) -> MetricResult:
        if self._strategy == "first":
            return existing
        if self._strategy == "last":
            return incoming
        # worst
        if self._STATUS_RANK[incoming.status] > self._STATUS_RANK[existing.status]:
            return incoming
        return existing
