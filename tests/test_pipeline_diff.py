"""Tests for pipewatch.pipeline_diff."""

from __future__ import annotations

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.pipeline_diff import DiffEntry, DiffReport, PipelineDiffer


def make_result(source: str, name: str, status: MetricStatus, value: float = 1.0) -> MetricResult:
    return MetricResult(
        source=source,
        metric=Metric(name=name, value=value),
        status=status,
        timestamp=None,
    )


@pytest.fixture
def differ() -> PipelineDiffer:
    return PipelineDiffer()


def test_empty_inputs_produce_empty_report(differ):
    report = differ.diff([], [])
    assert len(report.entries) == 0
    assert not report.has_differences()


def test_identical_results_have_no_differences(differ):
    r = make_result("src", "lag", MetricStatus.OK)
    report = differ.diff([r], [r])
    assert not report.has_differences()
    assert len(report.unchanged) == 1


def test_added_metric_detected(differ):
    after = make_result("src", "lag", MetricStatus.OK)
    report = differ.diff([], [after])
    assert len(report.added) == 1
    assert report.added[0].metric_name == "lag"
    assert report.has_differences()


def test_removed_metric_detected(differ):
    before = make_result("src", "lag", MetricStatus.OK)
    report = differ.diff([before], [])
    assert len(report.removed) == 1
    assert report.removed[0].source == "src"
    assert report.has_differences()


def test_status_change_detected(differ):
    before = make_result("src", "lag", MetricStatus.OK)
    after = make_result("src", "lag", MetricStatus.CRITICAL)
    report = differ.diff([before], [after])
    assert len(report.changed) == 1
    entry = report.changed[0]
    assert entry.before.status == MetricStatus.OK
    assert entry.after.status == MetricStatus.CRITICAL


def test_no_change_when_same_status(differ):
    before = make_result("src", "lag", MetricStatus.WARNING)
    after = make_result("src", "lag", MetricStatus.WARNING)
    report = differ.diff([before], [after])
    assert not report.has_differences()
    assert len(report.unchanged) == 1


def test_multiple_sources_diffed_independently(differ):
    before = [
        make_result("a", "m", MetricStatus.OK),
        make_result("b", "m", MetricStatus.WARNING),
    ]
    after = [
        make_result("a", "m", MetricStatus.CRITICAL),
        make_result("b", "m", MetricStatus.WARNING),
    ]
    report = differ.diff(before, after)
    assert len(report.changed) == 1
    assert report.changed[0].source == "a"
    assert len(report.unchanged) == 1


def test_diff_entry_str_added():
    entry = DiffEntry(source="s", metric_name="m", before=None,
                      after=make_result("s", "m", MetricStatus.OK))
    assert "ADDED" in str(entry)


def test_diff_entry_str_removed():
    entry = DiffEntry(source="s", metric_name="m",
                      before=make_result("s", "m", MetricStatus.OK), after=None)
    assert "REMOVED" in str(entry)


def test_diff_entry_str_changed():
    entry = DiffEntry(
        source="s", metric_name="m",
        before=make_result("s", "m", MetricStatus.OK),
        after=make_result("s", "m", MetricStatus.WARNING),
    )
    assert "CHANGED" in str(entry)


def test_diff_report_str_contains_summary(differ):
    after = make_result("src", "lag", MetricStatus.CRITICAL)
    report = differ.diff([], [after])
    summary = str(report)
    assert "+1" in summary
