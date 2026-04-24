"""Profiler: tracks execution timing for pipeline metric collections."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProfileEntry:
    source: str
    metric_name: str
    duration_seconds: float
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return (
            f"[{self.source}/{self.metric_name}] "
            f"{self.duration_seconds:.4f}s"
        )


@dataclass
class ProfileReport:
    entries: List[ProfileEntry]

    def slowest(self, n: int = 5) -> List[ProfileEntry]:
        return sorted(self.entries, key=lambda e: e.duration_seconds, reverse=True)[:n]

    def average_duration(self) -> Optional[float]:
        if not self.entries:
            return None
        return sum(e.duration_seconds for e in self.entries) / len(self.entries)

    def total_duration(self) -> float:
        return sum(e.duration_seconds for e in self.entries)

    def __str__(self) -> str:
        lines = [f"Profile Report ({len(self.entries)} entries)"]
        lines.append(f"  Total:   {self.total_duration():.4f}s")
        avg = self.average_duration()
        lines.append(f"  Average: {avg:.4f}s" if avg is not None else "  Average: N/A")
        lines.append("  Slowest:")
        for entry in self.slowest(3):
            lines.append(f"    {entry}")
        return "\n".join(lines)


class Profiler:
    def __init__(self) -> None:
        self._entries: List[ProfileEntry] = []

    def record(self, source: str, metric_name: str, duration_seconds: float) -> None:
        self._entries.append(
            ProfileEntry(
                source=source,
                metric_name=metric_name,
                duration_seconds=duration_seconds,
            )
        )

    def entries(self) -> List[ProfileEntry]:
        return list(self._entries)

    def report(self) -> ProfileReport:
        return ProfileReport(entries=list(self._entries))

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
