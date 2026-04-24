"""Lint MetricResult collections for common configuration and data issues."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from pipewatch.metrics import MetricResult, MetricStatus


@dataclass
class LintIssue:
    """A single linting finding."""

    severity: str  # "error" | "warning" | "info"
    source: str
    metric_name: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.source}/{self.metric_name}: {self.message}"


@dataclass
class LintReport:
    """Aggregated result of a lint run."""

    issues: List[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[LintIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_clean(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        if not self.issues:
            return "Lint passed: no issues found."
        lines = [str(i) for i in self.issues]
        lines.append(f"\n{len(self.errors)} error(s), {len(self.warnings)} warning(s).")
        return "\n".join(lines)


class PipelineLinter:
    """Runs a series of checks against a collection of MetricResults."""

    def lint(self, results: Sequence[MetricResult]) -> LintReport:
        report = LintReport()
        for result in results:
            self._check_missing_value(result, report)
            self._check_negative_value(result, report)
            self._check_no_thresholds_but_not_ok(result, report)
            self._check_empty_source(result, report)
        self._check_duplicate_names(results, report)
        return report

    # ------------------------------------------------------------------
    def _check_missing_value(self, r: MetricResult, report: LintReport) -> None:
        if r.value is None:
            report.issues.append(
                LintIssue("error", r.source, r.metric.name, "metric value is None")
            )

    def _check_negative_value(self, r: MetricResult, report: LintReport) -> None:
        if r.value is not None and r.value < 0:
            report.issues.append(
                LintIssue("warning", r.source, r.metric.name, f"negative value ({r.value})")
            )

    def _check_no_thresholds_but_not_ok(self, r: MetricResult, report: LintReport) -> None:
        m = r.metric
        has_thresholds = m.warning_threshold is not None or m.critical_threshold is not None
        if not has_thresholds and r.status != MetricStatus.OK:
            report.issues.append(
                LintIssue(
                    "error",
                    r.source,
                    m.name,
                    f"status is {r.status.value} but no thresholds are configured",
                )
            )

    def _check_empty_source(self, r: MetricResult, report: LintReport) -> None:
        if not r.source or not r.source.strip():
            report.issues.append(
                LintIssue("error", "<unknown>", r.metric.name, "source name is empty")
            )

    def _check_duplicate_names(self, results: Sequence[MetricResult], report: LintReport) -> None:
        seen: dict[tuple[str, str], int] = {}
        for r in results:
            key = (r.source, r.metric.name)
            seen[key] = seen.get(key, 0) + 1
        for (source, name), count in seen.items():
            if count > 1:
                report.issues.append(
                    LintIssue("warning", source, name, f"metric name appears {count} times")
                )
