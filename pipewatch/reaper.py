"""Reaper: remove stale MetricResults that exceed a max-age threshold."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from pipewatch.metrics import MetricResult


@dataclass
class ReaperConfig:
    max_age_seconds: float = 3600.0
    now: Optional[datetime] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")

    def _now(self) -> datetime:
        return self.now if self.now is not None else datetime.now(tz=timezone.utc)


@dataclass
class ReapReport:
    kept: List[MetricResult]
    removed: List[MetricResult]

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def kept_count(self) -> int:
        return len(self.kept)

    def __str__(self) -> str:
        return (
            f"ReapReport: kept={self.kept_count}, removed={self.removed_count}"
        )


class ResultReaper:
    """Filters out MetricResults whose timestamp is older than max_age_seconds."""

    def __init__(self, config: Optional[ReaperConfig] = None) -> None:
        self._config = config or ReaperConfig()

    def reap(self, results: List[MetricResult]) -> ReapReport:
        """Return a ReapReport partitioning *results* into kept and removed."""
        cutoff = self._config._now() - timedelta(seconds=self._config.max_age_seconds)
        kept: List[MetricResult] = []
        removed: List[MetricResult] = []
        for r in results:
            if r.timestamp is None or r.timestamp >= cutoff:
                kept.append(r)
            else:
                removed.append(r)
        return ReapReport(kept=kept, removed=removed)
