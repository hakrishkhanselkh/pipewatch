"""Tests for pipewatch.linter."""

from __future__ import annotations

import pytest

from pipewatch.linter import LintIssue, LintReport, PipelineLinter
from pipewatch.metrics import Metric, MetricResult, MetricStatus


def make_result(
    name: str = "latency",
    value: float | None = 1.0,
    status: MetricStatus = MetricStatus.OK,
    source: str = "pipeline_a",
    warning_threshold: float | None = 5.0,
    critical_threshold: float | None = 10.0,
) -> MetricResult:
    return MetricResult(
        metric=Metric(
            name=name,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        ),
        value=value,
        status=status,
        source=source,
    )


@pytest.fixture()
def linter() -> PipelineLinter:
    return PipelineLinter()


def test_clean_results_produce_no_issues(linter: PipelineLinter) -> None:
    results = [make_result(), make_result(name="throughput", value=100.0)]
    report = linter.lint(results)
    assert report.is_clean
    assert len(report.issues) == 0


def test_none_value_is_error(linter: PipelineLinter) -> None:
    report = linter.lint([make_result(value=None)])
    errors = report.errors
    assert len(errors) == 1
    assert "None" in errors[0].message


def test_negative_value_is_warning(linter: PipelineLinter) -> None:
    report = linter.lint([make_result(value=-3.5)])
    warnings = report.warnings
    assert any("negative" in w.message for w in warnings)


def test_non_ok_without_thresholds_is_error(linter: PipelineLinter) -> None:
    result = make_result(
        status=MetricStatus.WARNING,
        warning_threshold=None,
        critical_threshold=None,
    )
    report = linter.lint([result])
    assert not report.is_clean
    assert any("no thresholds" in e.message for e in report.errors)


def test_ok_without_thresholds_is_fine(linter: PipelineLinter) -> None:
    result = make_result(
        status=MetricStatus.OK,
        warning_threshold=None,
        critical_threshold=None,
    )
    report = linter.lint([result])
    assert report.is_clean


def test_empty_source_is_error(linter: PipelineLinter) -> None:
    report = linter.lint([make_result(source="")])
    assert any(e.severity == "error" for e in report.issues)


def test_duplicate_metric_names_are_warning(linter: PipelineLinter) -> None:
    results = [make_result(name="latency"), make_result(name="latency")]
    report = linter.lint(results)
    assert any("appears" in w.message for w in report.warnings)


def test_lint_issue_str() -> None:
    issue = LintIssue("error", "src", "metric", "something wrong")
    assert "[ERROR]" in str(issue)
    assert "src/metric" in str(issue)


def test_lint_report_str_clean() -> None:
    report = LintReport()
    assert "no issues" in str(report)


def test_lint_report_str_with_issues() -> None:
    report = LintReport(issues=[LintIssue("error", "s", "m", "bad")])
    text = str(report)
    assert "1 error" in text


def test_is_clean_false_when_errors_present() -> None:
    report = LintReport(issues=[LintIssue("error", "s", "m", "x")])
    assert not report.is_clean


def test_multiple_issues_accumulated(linter: PipelineLinter) -> None:
    results = [
        make_result(value=None),
        make_result(name="dup"),
        make_result(name="dup"),
    ]
    report = linter.lint(results)
    assert len(report.issues) >= 2
