"""Group MetricResults by an arbitrary key and compute per-group summaries."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class GroupSummary:
    """Aggregated view of a single group."""

    key: str
    results: List[MetricResult] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.results)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.results if r.status == MetricStatus.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.status == MetricStatus.WARNING)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.status == MetricStatus.OK)

    @property
    def worst_status(self) -> MetricStatus:
        if self.critical_count:
            return MetricStatus.CRITICAL
        if self.warning_count:
            return MetricStatus.WARNING
        return MetricStatus.OK

    def __str__(self) -> str:
        return (
            f"Group({self.key!r}: total={self.count}, "
            f"critical={self.critical_count}, warning={self.warning_count}, "
            f"ok={self.ok_count}, worst={self.worst_status.value})"
        )


class ResultGrouper:
    """Groups MetricResult objects by a caller-supplied key function."""

    def __init__(self, key_fn: Callable[[MetricResult], str]) -> None:
        self._key_fn = key_fn
        self._groups: Dict[str, GroupSummary] = {}

    def add(self, result: MetricResult) -> None:
        key = self._key_fn(result)
        if key not in self._groups:
            self._groups[key] = GroupSummary(key=key)
        self._groups[key].results.append(result)

    def add_all(self, results: List[MetricResult]) -> None:
        for r in results:
            self.add(r)

    def get(self, key: str) -> Optional[GroupSummary]:
        return self._groups.get(key)

    def all_groups(self) -> List[GroupSummary]:
        return list(self._groups.values())

    def keys(self) -> List[str]:
        return list(self._groups.keys())

    def __len__(self) -> int:
        return len(self._groups)
