"""Compare two sets of MetricResults and report changes in status."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class StatusChange:
    source: str
    name: str
    previous: MetricStatus
    current: MetricStatus

    def __str__(self) -> str:
        return (
            f"[{self.source}/{self.name}] "
            f"{self.previous.value} -> {self.current.value}"
        )

    @property
    def is_degraded(self) -> bool:
        order = [MetricStatus.OK, MetricStatus.WARNING, MetricStatus.CRITICAL]
        return order.index(self.current) > order.index(self.previous)

    @property
    def is_recovered(self) -> bool:
        return (
            self.previous != MetricStatus.OK
            and self.current == MetricStatus.OK
        )


@dataclass
class ComparisonReport:
    changes: List[StatusChange] = field(default_factory=list)
    new_sources: List[str] = field(default_factory=list)
    dropped_sources: List[str] = field(default_factory=list)

    @property
    def has_degradations(self) -> bool:
        return any(c.is_degraded for c in self.changes)

    @property
    def has_recoveries(self) -> bool:
        return any(c.is_recovered for c in self.changes)

    def summary(self) -> str:
        lines = []
        if self.changes:
            lines.append(f"{len(self.changes)} status change(s):")
            for c in self.changes:
                lines.append(f"  {c}")
        if self.new_sources:
            lines.append(f"New sources: {', '.join(self.new_sources)}")
        if self.dropped_sources:
            lines.append(f"Dropped sources: {', '.join(self.dropped_sources)}")
        if not lines:
            lines.append("No changes detected.")
        return "\n".join(lines)


class ResultComparator:
    """Compare two snapshots of MetricResults."""

    @staticmethod
    def _index(
        results: List[MetricResult],
    ) -> Dict[Tuple[str, str], MetricStatus]:
        return {(r.source, r.name): r.status for r in results}

    def compare(
        self,
        previous: List[MetricResult],
        current: List[MetricResult],
    ) -> ComparisonReport:
        prev_idx = self._index(previous)
        curr_idx = self._index(current)

        prev_sources = {r.source for r in previous}
        curr_sources = {r.source for r in current}

        report = ComparisonReport(
            new_sources=sorted(curr_sources - prev_sources),
            dropped_sources=sorted(prev_sources - curr_sources),
        )

        for key, curr_status in curr_idx.items():
            if key in prev_idx and prev_idx[key] != curr_status:
                report.changes.append(
                    StatusChange(
                        source=key[0],
                        name=key[1],
                        previous=prev_idx[key],
                        current=curr_status,
                    )
                )

        return report
