"""Tests for pipewatch.summarizer and the cli_summary entry-point."""
from __future__ import annotations

import json
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.summarizer import PipelineSummary, Summarizer


def make_result(name: str, source: str, value: float, status: MetricStatus) -> MetricResult:
    return MetricResult(metric=Metric(name=name, source=source, value=value), status=status)


@pytest.fixture()
def mixed_results():
    return [
        make_result("lag", "kafka", 10.0, MetricStatus.OK),
        make_result("lag", "kafka", 80.0, MetricStatus.WARNING),
        make_result("error_rate", "api", 5.0, MetricStatus.CRITICAL),
        make_result("throughput", "api", 100.0, MetricStatus.OK),
    ]


class TestSummarizer:
    def test_counts_are_correct(self, mixed_results):
        s = Summarizer().summarize(mixed_results)
        assert s.total == 4
        assert s.ok == 2
        assert s.warning == 1
        assert s.critical == 1

    def test_overall_status_critical_takes_priority(self, mixed_results):
        s = Summarizer().summarize(mixed_results)
        assert s.overall_status == MetricStatus.CRITICAL

    def test_overall_status_warning_when_no_critical(self):
        results = [
            make_result("a", "src", 1.0, MetricStatus.OK),
            make_result("b", "src", 2.0, MetricStatus.WARNING),
        ]
        s = Summarizer().summarize(results)
        assert s.overall_status == MetricStatus.WARNING

    def test_overall_status_ok_when_all_ok(self):
        results = [make_result("a", "src", 1.0, MetricStatus.OK)]
        s = Summarizer().summarize(results)
        assert s.overall_status == MetricStatus.OK

    def test_is_healthy_false_when_warning(self):
        results = [make_result("a", "src", 1.0, MetricStatus.WARNING)]
        assert not Summarizer().summarize(results).is_healthy

    def test_is_healthy_true_when_all_ok(self):
        results = [make_result("a", "src", 1.0, MetricStatus.OK)]
        assert Summarizer().summarize(results).is_healthy

    def test_sources_aggregated(self, mixed_results):
        s = Summarizer().summarize(mixed_results)
        assert s.sources["kafka"] == 2
        assert s.sources["api"] == 2

    def test_empty_results(self):
        s = Summarizer().summarize([])
        assert s.total == 0
        assert s.is_healthy

    def test_format_report_contains_status(self, mixed_results):
        summarizer = Summarizer()
        report = summarizer.format_report(summarizer.summarize(mixed_results))
        assert "CRITICAL" in report
        assert "kafka" in report
        assert "api" in report


class TestCliSummary:
    def _make_json_input(self, results):
        from pipewatch.exporters import _result_to_dict
        return json.dumps([_result_to_dict(r) for r in results])

    def test_exit_code_zero_when_healthy(self, tmp_path, mixed_results):
        f = tmp_path / "out.json"
        results = [make_result("a", "src", 1.0, MetricStatus.OK)]
        f.write_text(self._make_json_input(results))
        from pipewatch.cli_summary import main
        main(["--input", str(f)])

    def test_exit_code_two_on_critical(self, tmp_path, mixed_results):
        f = tmp_path / "out.json"
        f.write_text(self._make_json_input(mixed_results))
        from pipewatch.cli_summary import main
        with pytest.raises(SystemExit) as exc:
            main(["--input", str(f), "--fail-on-critical"])
        assert exc.value.code == 2

    def test_status_filter_applied(self, tmp_path, mixed_results):
        f = tmp_path / "out.json"
        f.write_text(self._make_json_input(mixed_results))
        from pipewatch.cli_summary import main
        # Should not raise even with --fail-on-critical because we filter to ok only
        main(["--input", str(f), "--status", "ok", "--fail-on-critical"])
