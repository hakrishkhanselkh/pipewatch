"""Correlate MetricResults across sources to detect related failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class CorrelationGroup:
    """A group of results that share the same metric name and non-OK status."""

    metric_name: str
    status: MetricStatus
    results: List[MetricResult] = field(default_factory=list)

    def __str__(self) -> str:
        sources = ", ".join(r.source for r in self.results)
        return (
            f"CorrelationGroup(metric={self.metric_name!r}, "
            f"status={self.status.value}, sources=[{sources}])"
        )

    @property
    def source_count(self) -> int:
        return len(self.results)


@dataclass
class CorrelationReport:
    """Summary of correlated failures found across sources."""

    groups: List[CorrelationGroup] = field(default_factory=list)

    @property
    def has_correlations(self) -> bool:
        return len(self.groups) > 0

    def by_metric(self, name: str) -> Optional[CorrelationGroup]:
        for g in self.groups:
            if g.metric_name == name:
                return g
        return None

    def __str__(self) -> str:
        if not self.groups:
            return "CorrelationReport: no correlated failures"
        lines = [f"CorrelationReport: {len(self.groups)} group(s)"]
        for g in self.groups:
            lines.append(f"  {g}")
        return "\n".join(lines)


class ResultCorrelator:
    """Detect metric names that are failing across multiple sources."""

    def __init__(self, min_sources: int = 2) -> None:
        if min_sources < 1:
            raise ValueError("min_sources must be >= 1")
        self._min_sources = min_sources
        self._results: List[MetricResult] = []

    def add(self, result: MetricResult) -> None:
        self._results.append(result)

    def add_all(self, results: List[MetricResult]) -> None:
        for r in results:
            self.add(r)

    def correlate(self) -> CorrelationReport:
        """Return groups of results sharing the same metric name and unhealthy status."""
        buckets: Dict[str, List[MetricResult]] = {}
        for r in self._results:
            if r.status == MetricStatus.OK:
                continue
            buckets.setdefault(r.metric_name, []).append(r)

        groups: List[CorrelationGroup] = []
        for metric_name, members in buckets.items():
            if len(members) < self._min_sources:
                continue
            # Dominant status: CRITICAL beats WARNING
            dominant = (
                MetricStatus.CRITICAL
                if any(m.status == MetricStatus.CRITICAL for m in members)
                else MetricStatus.WARNING
            )
            groups.append(
                CorrelationGroup(
                    metric_name=metric_name,
                    status=dominant,
                    results=list(members),
                )
            )

        groups.sort(key=lambda g: (g.status != MetricStatus.CRITICAL, g.metric_name))
        return CorrelationReport(groups=groups)

    def clear(self) -> None:
        self._results.clear()
