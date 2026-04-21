"""Tests for pipewatch.reporter."""

from __future__ import annotations

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.reporter import Reporter, PipelineReport, ReportSection


def make_result(
    name: str,
    source: str,
    status: MetricStatus,
    value: float = 1.0,
    message: str | None = None,
) -> MetricResult:
    return MetricResult(
        metric=Metric(name=name, source=source),
        value=value,
        status=status,
        message=message,
        source=source,
    )


@pytest.fixture
def mixed_results():
    return [
        make_result("row_count", "db", MetricStatus.OK, value=500),
        make_result("latency", "db", MetricStatus.WARNING, value=320, message="High latency"),
        make_result("error_rate", "api", MetricStatus.CRITICAL, value=0.15, message="Too many errors"),
        make_result("throughput", "api", MetricStatus.OK, value=1000),
    ]


class TestReporter:
    def test_build_returns_pipeline_report(self, mixed_results):
        reporter = Reporter()
        report = reporter.build(mixed_results)
        assert isinstance(report, PipelineReport)

    def test_report_contains_all_sources(self, mixed_results):
        reporter = Reporter()
        report = reporter.build(mixed_results)
        titles = [s.title for s in report.sections]
        assert "db" in titles
        assert "api" in titles

    def test_hide_ok_excludes_ok_results(self, mixed_results):
        reporter = Reporter(include_ok=False)
        report = reporter.build(mixed_results)
        rendered = report.render()
        assert "row_count" not in rendered
        assert "throughput" not in rendered
        assert "latency" in rendered
        assert "error_rate" in rendered

    def test_include_ok_shows_all_results(self, mixed_results):
        reporter = Reporter(include_ok=True)
        report = reporter.build(mixed_results)
        rendered = report.render()
        assert "row_count" in rendered
        assert "throughput" in rendered

    def test_message_appears_in_render(self, mixed_results):
        reporter = Reporter()
        report = reporter.build(mixed_results)
        rendered = report.render()
        assert "High latency" in rendered
        assert "Too many errors" in rendered

    def test_status_symbols_present(self, mixed_results):
        reporter = Reporter()
        report = reporter.build(mixed_results)
        rendered = report.render()
        assert "[OK]" in rendered
        assert "[WARN]" in rendered
        assert "[CRIT]" in rendered

    def test_custom_title(self, mixed_results):
        reporter = Reporter()
        report = reporter.build(mixed_results, title="My Custom Report")
        assert "My Custom Report" in report.render()

    def test_empty_results_renders_without_error(self):
        reporter = Reporter()
        report = reporter.build([])
        rendered = report.render()
        assert isinstance(rendered, str)

    def test_report_str_equals_render(self, mixed_results):
        reporter = Reporter()
        report = reporter.build(mixed_results)
        assert str(report) == report.render()

    def test_section_render_includes_title(self):
        section = ReportSection(title="test-source", lines=["  [OK] metric: 1.0"])
        rendered = section.render()
        assert "=== test-source ===" in rendered
        assert "[OK] metric" in rendered
