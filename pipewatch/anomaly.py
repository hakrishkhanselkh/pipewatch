"""Anomaly detection for pipeline metric results.

Uses a simple statistical approach (z-score and IQR) to flag metric
values that deviate significantly from their recent history.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class AnomalyFlag:
    """Represents a detected anomaly for a single metric result."""

    result: MetricResult
    z_score: Optional[float]
    deviation: float  # absolute deviation from mean
    mean: float
    stddev: float
    method: str  # 'zscore' or 'iqr'

    def __str__(self) -> str:
        z = f", z={self.z_score:.2f}" if self.z_score is not None else ""
        return (
            f"[ANOMALY] {self.result.source}/{self.result.name} "
            f"value={self.result.value:.4g} mean={self.mean:.4g} "
            f"stddev={self.stddev:.4g}{z} method={self.method}"
        )


@dataclass
class AnomalyReport:
    """Collects all anomaly flags produced during a detection run."""

    flags: List[AnomalyFlag] = field(default_factory=list)

    @property
    def has_anomalies(self) -> bool:
        return len(self.flags) > 0

    def __len__(self) -> int:
        return len(self.flags)

    def __str__(self) -> str:
        if not self.flags:
            return "AnomalyReport: no anomalies detected"
        lines = [f"AnomalyReport: {len(self.flags)} anomaly(ies) detected"]
        for flag in self.flags:
            lines.append(f"  {flag}")
        return "\n".join(lines)


class AnomalyDetector:
    """Detects anomalous metric values using historical baselines.

    Each unique (source, name) pair maintains its own rolling window of
    past values.  When a new result arrives it is compared against the
    window using a z-score test (if stddev > 0) or an IQR fence test as
    a fallback.

    Args:
        window_size: Maximum number of historical values to retain per
            metric.  Older values are discarded automatically.
        z_threshold: Number of standard deviations beyond which a value
            is considered anomalous (default 3.0).
        iqr_multiplier: IQR fence multiplier used when stddev is zero
            (default 1.5, matching Tukey's rule).
        min_samples: Minimum history length required before anomaly
            detection is attempted (default 5).
    """

    def __init__(
        self,
        window_size: int = 50,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        min_samples: int = 5,
    ) -> None:
        self._window_size = window_size
        self._z_threshold = z_threshold
        self._iqr_multiplier = iqr_multiplier
        self._min_samples = min_samples
        self._history: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(self, result: MetricResult) -> None:
        """Record a result value into the detector's history without
        performing anomaly detection."""
        if result.value is None:
            return
        key = self._key(result)
        window = self._history.setdefault(key, [])
        window.append(result.value)
        if len(window) > self._window_size:
            window.pop(0)

    def check(self, result: MetricResult) -> Optional[AnomalyFlag]:
        """Check whether *result* is anomalous given current history.

        Returns an :class:`AnomalyFlag` if the value is anomalous, or
        ``None`` if the value looks normal (or there is insufficient
        history).

        Note: this method does **not** add the value to history.  Call
        :meth:`observe` separately if you want to update the window.
        """
        if result.value is None:
            return None
        key = self._key(result)
        history = self._history.get(key, [])
        if len(history) < self._min_samples:
            return None

        mean = statistics.mean(history)
        stddev = statistics.pstdev(history)  # population stddev

        if stddev > 0:
            z = (result.value - mean) / stddev
            if abs(z) >= self._z_threshold:
                return AnomalyFlag(
                    result=result,
                    z_score=z,
                    deviation=abs(result.value - mean),
                    mean=mean,
                    stddev=stddev,
                    method="zscore",
                )
            return None

        # Fallback: IQR fence when all historical values are identical
        sorted_h = sorted(history)
        n = len(sorted_h)
        q1 = sorted_h[n // 4]
        q3 = sorted_h[(3 * n) // 4]
        iqr = q3 - q1
        lower = q1 - self._iqr_multiplier * iqr
        upper = q3 + self._iqr_multiplier * iqr
        if result.value < lower or result.value > upper:
            return AnomalyFlag(
                result=result,
                z_score=None,
                deviation=abs(result.value - mean),
                mean=mean,
                stddev=stddev,
                method="iqr",
            )
        return None

    def detect(self, results: List[MetricResult]) -> AnomalyReport:
        """Run anomaly detection over a batch of results.

        Each result is first checked against existing history, then
        observed so that later results in the same batch can benefit from
        the updated window.

        Returns an :class:`AnomalyReport` containing all flagged results.
        """
        report = AnomalyReport()
        for result in results:
            flag = self.check(result)
            if flag is not None:
                report.flags.append(flag)
            self.observe(result)
        return report

    def reset(self, source: Optional[str] = None, name: Optional[str] = None) -> None:
        """Clear history for a specific metric or for all metrics.

        If both *source* and *name* are given, only that metric's history
        is cleared.  If neither is given, all history is cleared.
        """
        if source is not None and name is not None:
            self._history.pop(f"{source}:{name}", None)
        else:
            self._history.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(result: MetricResult) -> str:
        return f"{result.source}:{result.name}"
