"""Filtering utilities for MetricResult collections."""

from typing import List, Optional, Callable
from pipewatch.metrics import MetricResult, MetricStatus


class ResultFilter:
    """Chainable filter builder for MetricResult lists."""

    def __init__(self, results: List[MetricResult]):
        self._results = list(results)

    def by_status(self, *statuses: MetricStatus) -> "ResultFilter":
        """Keep only results matching one of the given statuses."""
        status_set = set(statuses)
        return ResultFilter(
            [r for r in self._results if r.status in status_set]
        )

    def by_source(self, source: str) -> "ResultFilter":
        """Keep only results whose metric source matches (substring)."""
        return ResultFilter(
            [r for r in self._results if source in r.metric.source]
        )

    def by_name(self, name: str) -> "ResultFilter":
        """Keep only results whose metric name matches (substring)."""
        return ResultFilter(
            [r for r in self._results if name in r.metric.name]
        )

    def unhealthy(self) -> "ResultFilter":
        """Keep only WARNING and CRITICAL results."""
        return self.by_status(MetricStatus.WARNING, MetricStatus.CRITICAL)

    def above_value(self, threshold: float) -> "ResultFilter":
        """Keep only results where the metric value exceeds threshold."""
        return ResultFilter(
            [r for r in self._results if r.value is not None and r.value > threshold]
        )

    def matching(self, predicate: Callable[[MetricResult], bool]) -> "ResultFilter":
        """Keep only results satisfying an arbitrary predicate."""
        return ResultFilter([r for r in self._results if predicate(r)])

    def results(self) -> List[MetricResult]:
        """Return the filtered list of MetricResults."""
        return self._results

    def __len__(self) -> int:
        return len(self._results)

    def __repr__(self) -> str:
        return f"ResultFilter({len(self._results)} results)"
