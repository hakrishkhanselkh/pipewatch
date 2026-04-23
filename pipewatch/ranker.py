"""Rank MetricResults by severity and value to surface the most critical issues first."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.metrics import MetricResult, MetricStatus

# Lower rank number = higher priority
_STATUS_PRIORITY: dict[MetricStatus, int] = {
    MetricStatus.CRITICAL: 0,
    MetricStatus.WARNING: 1,
    MetricStatus.OK: 2,
}


@dataclass
class RankedResult:
    """A MetricResult decorated with its computed rank position."""

    result: MetricResult
    rank: int

    def __str__(self) -> str:
        return f"[{self.rank}] {self.result.source}/{self.result.name} — {self.result.status.value} (value={self.result.value})"


class ResultRanker:
    """Ranks a list of MetricResults by status severity then by absolute value descending."""

    def __init__(self, results: Optional[List[MetricResult]] = None) -> None:
        self._results: List[MetricResult] = list(results) if results else []

    def add(self, result: MetricResult) -> None:
        """Add a single result to the ranking pool."""
        self._results.append(result)

    def rank(self) -> List[RankedResult]:
        """Return results sorted by severity then value, with 1-based rank positions."""
        sorted_results = sorted(
            self._results,
            key=lambda r: (
                _STATUS_PRIORITY.get(r.status, 99),
                -(r.value if r.value is not None else 0.0),
            ),
        )
        return [
            RankedResult(result=r, rank=i + 1)
            for i, r in enumerate(sorted_results)
        ]

    def top(self, n: int) -> List[RankedResult]:
        """Return the top-n ranked results."""
        return self.rank()[:n]

    def __len__(self) -> int:
        return len(self._results)
