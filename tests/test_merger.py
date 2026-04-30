"""Tests for pipewatch.merger."""
from __future__ import annotations

import pytest

from pipewatch.merger import ResultMerger, _default_key
from pipewatch.metrics import Metric, MetricResult, MetricStatus


def make_result(
    name: str = "latency",
    source: str = "db",
    status: MetricStatus = MetricStatus.OK,
    value: float = 1.0,
) -> MetricResult:
    metric = Metric(name=name, source=source)
    return MetricResult(metric=metric, value=value, status=status)


# ---------------------------------------------------------------------------
# _default_key
# ---------------------------------------------------------------------------

def test_default_key_uses_source_and_name():
    r = make_result(name="cpu", source="host-1")
    assert _default_key(r) == ("host-1", "cpu")


# ---------------------------------------------------------------------------
# ResultMerger – basic merging
# ---------------------------------------------------------------------------

def test_empty_streams_produce_empty_report():
    merger = ResultMerger()
    report = merger.merge([], [])
    assert report.results == []
    assert report.duplicate_count == 0
    assert report.source_count == 0


def test_single_stream_no_duplicates():
    merger = ResultMerger()
    results = [make_result("a"), make_result("b"), make_result("c")]
    report = merger.merge(results)
    assert len(report.results) == 3
    assert report.duplicate_count == 0


def test_source_count_reflects_unique_sources():
    merger = ResultMerger()
    r1 = make_result(source="db")
    r2 = make_result(source="cache")
    r3 = make_result(source="db")
    report = merger.merge([r1, r2, r3])
    assert report.source_count == 2


# ---------------------------------------------------------------------------
# Conflict strategies
# ---------------------------------------------------------------------------

def test_strategy_worst_keeps_critical_over_ok():
    merger = ResultMerger(strategy="worst")
    ok = make_result(status=MetricStatus.OK, value=1.0)
    critical = make_result(status=MetricStatus.CRITICAL, value=99.0)
    report = merger.merge([ok], [critical])
    assert len(report.results) == 1
    assert report.results[0].status == MetricStatus.CRITICAL
    assert report.duplicate_count == 1


def test_strategy_worst_keeps_warning_over_ok():
    merger = ResultMerger(strategy="worst")
    ok = make_result(status=MetricStatus.OK)
    warning = make_result(status=MetricStatus.WARNING)
    report = merger.merge([ok], [warning])
    assert report.results[0].status == MetricStatus.WARNING


def test_strategy_first_keeps_first_seen():
    merger = ResultMerger(strategy="first")
    first = make_result(status=MetricStatus.OK, value=1.0)
    second = make_result(status=MetricStatus.CRITICAL, value=99.0)
    report = merger.merge([first], [second])
    assert report.results[0].status == MetricStatus.OK


def test_strategy_last_keeps_last_seen():
    merger = ResultMerger(strategy="last")
    first = make_result(status=MetricStatus.OK, value=1.0)
    second = make_result(status=MetricStatus.CRITICAL, value=99.0)
    report = merger.merge([first], [second])
    assert report.results[0].status == MetricStatus.CRITICAL


def test_invalid_strategy_raises():
    with pytest.raises(ValueError, match="Unknown strategy"):
        ResultMerger(strategy="random")


# ---------------------------------------------------------------------------
# Custom key function
# ---------------------------------------------------------------------------

def test_custom_key_fn_groups_differently():
    # Group only by metric name, ignoring source
    merger = ResultMerger(strategy="worst", key_fn=lambda r: (r.metric.name,))
    r1 = make_result(name="cpu", source="host-1", status=MetricStatus.OK)
    r2 = make_result(name="cpu", source="host-2", status=MetricStatus.WARNING)
    report = merger.merge([r1, r2])
    assert len(report.results) == 1
    assert report.results[0].status == MetricStatus.WARNING
    assert report.duplicate_count == 1
