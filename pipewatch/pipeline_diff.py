"""Compare two sets of pipeline results and produce a structured diff report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class DiffEntry:
    source: str
    metric_name: str
    before: Optional[MetricResult]
    after: Optional[MetricResult]

    @property
    def is_added(self) -> bool:
        return self.before is None and self.after is not None

    @property
    def is_removed(self) -> bool:
        return self.before is not None and self.after is None

    @property
    def is_changed(self) -> bool:
        return (
            self.before is not None
            and self.after is not None
            and self.before.status != self.after.status
        )

    def __str__(self) -> str:
        if self.is_added:
            return f"[ADDED]   {self.source}/{self.metric_name} -> {self.after.status.value}"
        if self.is_removed:
            return f"[REMOVED] {self.source}/{self.metric_name} (was {self.before.status.value})"
        if self.is_changed:
            return (
                f"[CHANGED] {self.source}/{self.metric_name}: "
                f"{self.before.status.value} -> {self.after.status.value}"
            )
        return f"[SAME]    {self.source}/{self.metric_name}: {self.after.status.value}"


@dataclass
class DiffReport:
    entries: List[DiffEntry] = field(default_factory=list)

    @property
    def added(self) -> List[DiffEntry]:
        return [e for e in self.entries if e.is_added]

    @property
    def removed(self) -> List[DiffEntry]:
        return [e for e in self.entries if e.is_removed]

    @property
    def changed(self) -> List[DiffEntry]:
        return [e for e in self.entries if e.is_changed]

    @property
    def unchanged(self) -> List[DiffEntry]:
        return [e for e in self.entries if not (e.is_added or e.is_removed or e.is_changed)]

    def has_differences(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def __str__(self) -> str:
        lines = [f"DiffReport: +{len(self.added)} -{len(self.removed)} ~{len(self.changed)}"]
        for entry in self.entries:
            if entry.is_added or entry.is_removed or entry.is_changed:
                lines.append(f"  {entry}")
        return "\n".join(lines)


class PipelineDiffer:
    """Compute a diff between two lists of MetricResult."""

    def diff(self, before: List[MetricResult], after: List[MetricResult]) -> DiffReport:
        def key(r: MetricResult) -> Tuple[str, str]:
            return (r.source, r.metric.name)

        before_map: Dict[Tuple[str, str], MetricResult] = {key(r): r for r in before}
        after_map: Dict[Tuple[str, str], MetricResult] = {key(r): r for r in after}

        all_keys = sorted(set(before_map) | set(after_map))
        entries = [
            DiffEntry(
                source=k[0],
                metric_name=k[1],
                before=before_map.get(k),
                after=after_map.get(k),
            )
            for k in all_keys
        ]
        return DiffReport(entries=entries)
