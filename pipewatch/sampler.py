"""Sampler: probabilistic and rate-based sampling of MetricResults."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class SamplerConfig:
    """Configuration for the Sampler."""

    rate: float = 1.0  # fraction of results to keep (0.0 – 1.0)
    always_keep_statuses: tuple = (MetricStatus.CRITICAL,)
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if not (0.0 < self.rate <= 1.0):
            raise ValueError(f"rate must be in (0.0, 1.0], got {self.rate}")


@dataclass
class SampleReport:
    """Summary produced by a sampling pass."""

    total: int
    kept: int
    dropped: int
    results: List[MetricResult] = field(default_factory=list)

    def __str__(self) -> str:
        pct = (self.kept / self.total * 100) if self.total else 0.0
        return (
            f"SampleReport: {self.kept}/{self.total} kept "
            f"({pct:.1f}%), {self.dropped} dropped"
        )


class ResultSampler:
    """Down-samples a list of MetricResults according to a SamplerConfig."""

    def __init__(self, config: Optional[SamplerConfig] = None) -> None:
        self._config = config or SamplerConfig()
        self._rng = random.Random(self._config.seed)

    @property
    def config(self) -> SamplerConfig:
        return self._config

    def sample(self, results: List[MetricResult]) -> SampleReport:
        """Return a SampleReport containing the sampled subset."""
        kept: List[MetricResult] = []
        dropped = 0

        for result in results:
            if result.status in self._config.always_keep_statuses:
                kept.append(result)
            elif self._rng.random() < self._config.rate:
                kept.append(result)
            else:
                dropped += 1

        return SampleReport(
            total=len(results),
            kept=len(kept),
            dropped=dropped,
            results=kept,
        )
