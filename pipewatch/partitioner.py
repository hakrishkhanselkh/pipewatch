"""Partition MetricResults into named buckets based on configurable rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from pipewatch.metrics import MetricResult


@dataclass
class Partition:
    """A named collection of MetricResults."""

    name: str
    results: List[MetricResult] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.results)

    def __str__(self) -> str:
        return f"Partition({self.name!r}, count={len(self.results)})"


@dataclass
class PartitionReport:
    """Result of partitioning a list of MetricResults."""

    partitions: Dict[str, Partition] = field(default_factory=dict)
    unmatched: List[MetricResult] = field(default_factory=list)

    def get(self, name: str) -> Optional[Partition]:
        return self.partitions.get(name)

    def partition_names(self) -> List[str]:
        return list(self.partitions.keys())

    def __str__(self) -> str:
        parts = ", ".join(
            f"{n}={len(p)}" for n, p in self.partitions.items()
        )
        return f"PartitionReport({parts}, unmatched={len(self.unmatched)})"


PartitionPredicate = Callable[[MetricResult], bool]


class ResultPartitioner:
    """Assigns MetricResults to named buckets via ordered predicate rules."""

    def __init__(self, default_bucket: Optional[str] = None) -> None:
        self._rules: List[tuple[str, PartitionPredicate]] = []
        self._default_bucket = default_bucket

    def add_rule(self, name: str, predicate: PartitionPredicate) -> None:
        """Register a named partition rule. Rules are evaluated in insertion order."""
        self._rules.append((name, predicate))

    def partition(self, results: List[MetricResult]) -> PartitionReport:
        """Partition *results* and return a PartitionReport."""
        report = PartitionReport()
        for name, _ in self._rules:
            report.partitions[name] = Partition(name=name)
        if self._default_bucket and self._default_bucket not in report.partitions:
            report.partitions[self._default_bucket] = Partition(name=self._default_bucket)

        for result in results:
            placed = False
            for name, predicate in self._rules:
                if predicate(result):
                    report.partitions[name].results.append(result)
                    placed = True
                    break
            if not placed:
                if self._default_bucket:
                    report.partitions[self._default_bucket].results.append(result)
                else:
                    report.unmatched.append(result)

        return report
