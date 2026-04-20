"""Tests for pipewatch.comparator."""

import pytest

from pipewatch.comparator import ComparisonReport, ResultComparator, StatusChange
from pipewatch.metrics import MetricResult, MetricStatus


def make_result(
    source: str,
    name: str,
    status: MetricStatus,
    value: float = 1.0,
) -> MetricResult:
    return MetricResult(source=source, name=name, value=value, status=status)


@pytest.fixture
def comparator() -> ResultComparator:
    return ResultComparator()


def test_no_changes_returns_empty_report(comparator):
    results = [make_result("src", "m1", MetricStatus.OK)]
    report = comparator.compare(results, results)
    assert report.changes == []
    assert report.new_sources == []
    assert report.dropped_sources == []


def test_detects_status_change(comparator):
    prev = [make_result("src", "m1", MetricStatus.OK)]
    curr = [make_result("src", "m1", MetricStatus.WARNING)]
    report = comparator.compare(prev, curr)
    assert len(report.changes) == 1
    assert report.changes[0].previous == MetricStatus.OK
    assert report.changes[0].current == MetricStatus.WARNING


def test_is_degraded_ok_to_warning():
    change = StatusChange("s", "m", MetricStatus.OK, MetricStatus.WARNING)
    assert change.is_degraded is True
    assert change.is_recovered is False


def test_is_degraded_ok_to_critical():
    change = StatusChange("s", "m", MetricStatus.OK, MetricStatus.CRITICAL)
    assert change.is_degraded is True


def test_is_recovered_critical_to_ok():
    change = StatusChange("s", "m", MetricStatus.CRITICAL, MetricStatus.OK)
    assert change.is_recovered is True
    assert change.is_degraded is False


def test_new_source_detected(comparator):
    prev = [make_result("src_a", "m1", MetricStatus.OK)]
    curr = [
        make_result("src_a", "m1", MetricStatus.OK),
        make_result("src_b", "m2", MetricStatus.OK),
    ]
    report = comparator.compare(prev, curr)
    assert "src_b" in report.new_sources


def test_dropped_source_detected(comparator):
    prev = [
        make_result("src_a", "m1", MetricStatus.OK),
        make_result("src_b", "m2", MetricStatus.OK),
    ]
    curr = [make_result("src_a", "m1", MetricStatus.OK)]
    report = comparator.compare(prev, curr)
    assert "src_b" in report.dropped_sources


def test_has_degradations_flag(comparator):
    prev = [make_result("s", "m", MetricStatus.OK)]
    curr = [make_result("s", "m", MetricStatus.CRITICAL)]
    report = comparator.compare(prev, curr)
    assert report.has_degradations is True
    assert report.has_recoveries is False


def test_has_recoveries_flag(comparator):
    prev = [make_result("s", "m", MetricStatus.CRITICAL)]
    curr = [make_result("s", "m", MetricStatus.OK)]
    report = comparator.compare(prev, curr)
    assert report.has_recoveries is True
    assert report.has_degradations is False


def test_summary_no_changes(comparator):
    results = [make_result("s", "m", MetricStatus.OK)]
    report = comparator.compare(results, results)
    assert "No changes" in report.summary()


def test_summary_with_changes(comparator):
    prev = [make_result("src", "latency", MetricStatus.OK)]
    curr = [make_result("src", "latency", MetricStatus.WARNING)]
    report = comparator.compare(prev, curr)
    summary = report.summary()
    assert "src/latency" in summary
    assert "ok" in summary.lower() or "warning" in summary.lower()


def test_status_change_str():
    change = StatusChange("db", "row_count", MetricStatus.OK, MetricStatus.CRITICAL)
    text = str(change)
    assert "db/row_count" in text
    assert "ok" in text.lower()
    assert "critical" in text.lower()
