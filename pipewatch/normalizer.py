"""Normalizer: rescale metric values to a 0–1 range for cross-source comparison."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.metrics import MetricResult


@dataclass
class NormalizedResult:
    """A MetricResult paired with its normalized value."""

    result: MetricResult
    normalized_value: Optional[float]

    def __str__(self) -> str:
        nv = f"{self.normalized_value:.4f}" if self.normalized_value is not None else "n/a"
        return (
            f"{self.result.source}/{self.result.name} "
            f"raw={self.result.value} normalized={nv}"
        )


@dataclass
class NormalizerConfig:
    """Per-metric min/max bounds used for normalization."""

    min_value: float = 0.0
    max_value: float = 1.0

    def __post_init__(self) -> None:
        if self.min_value >= self.max_value:
            raise ValueError(
                f"min_value ({self.min_value}) must be less than max_value ({self.max_value})"
            )


class ResultNormalizer:
    """Normalize MetricResult values to [0, 1] using registered per-metric configs."""

    def __init__(self) -> None:
        self._configs: Dict[str, NormalizerConfig] = {}

    def register(self, metric_name: str, config: NormalizerConfig) -> None:
        """Register a normalization config for *metric_name*."""
        self._configs[metric_name] = config

    def normalize_one(self, result: MetricResult) -> NormalizedResult:
        """Return a NormalizedResult for *result*.

        If no config is registered for the metric the normalized value is None.
        """
        cfg = self._configs.get(result.name)
        if cfg is None or result.value is None:
            return NormalizedResult(result=result, normalized_value=None)
        span = cfg.max_value - cfg.min_value
        normalized = (result.value - cfg.min_value) / span
        normalized = max(0.0, min(1.0, normalized))
        return NormalizedResult(result=result, normalized_value=normalized)

    def normalize(self, results: List[MetricResult]) -> List[NormalizedResult]:
        """Normalize a list of MetricResults."""
        return [self.normalize_one(r) for r in results]

    @property
    def registered_metrics(self) -> List[str]:
        """Return a sorted list of metric names that have registered configs."""
        return sorted(self._configs)
