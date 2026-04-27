"""Health scorer: assigns a numeric health score (0–100) to a collection of MetricResults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus

# Weight per status (higher = worse)
_STATUS_WEIGHT: dict[MetricStatus, float] = {
    MetricStatus.OK: 0.0,
    MetricStatus.WARNING: 0.5,
    MetricStatus.CRITICAL: 1.0,
}


@dataclass
class ScoreReport:
    """Result of scoring a batch of MetricResults."""

    score: float  # 0 (worst) – 100 (best)
    total: int
    ok_count: int
    warning_count: int
    critical_count: int
    grade: str = field(init=False)

    def __post_init__(self) -> None:
        if self.score >= 90:
            self.grade = "A"
        elif self.score >= 75:
            self.grade = "B"
        elif self.score >= 50:
            self.grade = "C"
        elif self.score >= 25:
            self.grade = "D"
        else:
            self.grade = "F"

    def __str__(self) -> str:
        return (
            f"Score: {self.score:.1f}/100 (Grade {self.grade}) "
            f"| OK={self.ok_count} WARN={self.warning_count} CRIT={self.critical_count}"
        )


class ResultScorer:
    """Computes an aggregate health score from a list of MetricResults."""

    def __init__(self, warning_weight: float = 0.5, critical_weight: float = 1.0) -> None:
        self._weights: dict[MetricStatus, float] = {
            MetricStatus.OK: 0.0,
            MetricStatus.WARNING: warning_weight,
            MetricStatus.CRITICAL: critical_weight,
        }

    def score(self, results: List[MetricResult]) -> ScoreReport:
        """Return a ScoreReport for *results*. Returns 100 when the list is empty."""
        if not results:
            return ScoreReport(
                score=100.0, total=0, ok_count=0, warning_count=0, critical_count=0
            )

        counts = {s: 0 for s in MetricStatus}
        for r in results:
            counts[r.status] += 1

        total = len(results)
        penalty = sum(
            self._weights[status] * count for status, count in counts.items()
        )
        # Max possible penalty if every result were CRITICAL
        max_penalty = self._weights[MetricStatus.CRITICAL] * total
        raw_score = 100.0 * (1.0 - penalty / max_penalty) if max_penalty else 100.0
        score = max(0.0, min(100.0, raw_score))

        return ScoreReport(
            score=round(score, 2),
            total=total,
            ok_count=counts[MetricStatus.OK],
            warning_count=counts[MetricStatus.WARNING],
            critical_count=counts[MetricStatus.CRITICAL],
        )
