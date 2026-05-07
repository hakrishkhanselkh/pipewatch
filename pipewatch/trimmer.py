"""Trimmer: remove results whose values fall outside a specified numeric range."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.metrics import MetricResult


@dataclass
class TrimConfig:
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def __post_init__(self) -> None:
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError(
                    f"min_value ({self.min_value}) must not exceed "
                    f"max_value ({self.max_value})"
                )


@dataclass
class TrimReport:
    kept: List[MetricResult] = field(default_factory=list)
    removed: List[MetricResult] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def kept_count(self) -> int:
        return len(self.kept)

    def __str__(self) -> str:
        return (
            f"TrimReport: kept={self.kept_count}, removed={self.removed_count}"
        )


class ResultTrimmer:
    """Filters out MetricResults whose value is outside [min_value, max_value].

    Results with a ``None`` value are always kept.
    """

    def __init__(self, config: TrimConfig) -> None:
        self._config = config

    def trim(self, results: List[MetricResult]) -> TrimReport:
        report = TrimReport()
        for result in results:
            if self._should_remove(result):
                report.removed.append(result)
            else:
                report.kept.append(result)
        return report

    def _should_remove(self, result: MetricResult) -> bool:
        value = result.value
        if value is None:
            return False
        if self._config.min_value is not None and value < self._config.min_value:
            return True
        if self._config.max_value is not None and value > self._config.max_value:
            return True
        return False
