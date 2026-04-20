"""Summarize a collection of MetricResults into a health report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class PipelineSummary:
    """Aggregate health statistics for a set of MetricResults."""

    total: int = 0
    ok: int = 0
    warning: int = 0
    critical: int = 0
    sources: Dict[str, int] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """True only when there are no warning or critical results."""
        return self.warning == 0 and self.critical == 0

    @property
    def overall_status(self) -> MetricStatus:
        if self.critical > 0:
            return MetricStatus.CRITICAL
        if self.warning > 0:
            return MetricStatus.WARNING
        return MetricStatus.OK

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"PipelineSummary(total={self.total}, ok={self.ok}, "
            f"warning={self.warning}, critical={self.critical}, "
            f"status={self.overall_status.value})"
        )


class Summarizer:
    """Build a PipelineSummary from a list of MetricResults."""

    def summarize(self, results: List[MetricResult]) -> PipelineSummary:
        summary = PipelineSummary(total=len(results))

        for result in results:
            status = result.status
            if status == MetricStatus.OK:
                summary.ok += 1
            elif status == MetricStatus.WARNING:
                summary.warning += 1
            elif status == MetricStatus.CRITICAL:
                summary.critical += 1

            source = result.metric.source
            summary.sources[source] = summary.sources.get(source, 0) + 1

        return summary

    def format_report(self, summary: PipelineSummary) -> str:
        """Return a human-readable multi-line report string."""
        lines = [
            f"Overall status : {summary.overall_status.value.upper()}",
            f"Total metrics  : {summary.total}",
            f"  OK           : {summary.ok}",
            f"  Warning      : {summary.warning}",
            f"  Critical     : {summary.critical}",
            "Sources:",
        ]
        for src, count in sorted(summary.sources.items()):
            lines.append(f"  {src}: {count} metric(s)")
        return "\n".join(lines)
