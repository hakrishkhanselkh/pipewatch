"""Tests for pipewatch.filters.ResultFilter."""

import pytest
from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.filters import ResultFilter


def make_result(
    name: str,
    source: str,
    value: float,
    status: MetricStatus,
) -> MetricResult:
    metric = Metric(name=name, source=source)
    return MetricResult(metric=metric, value=value, status=status)


@pytest.fixture()
def sample_results():
    return [
        make_result("row_count", "warehouse", 1000.0, MetricStatus.OK),
        make_result("latency", "warehouse", 320.0, MetricStatus.WARNING),
        make_result("error_rate", "api", 0.15, MetricStatus.CRITICAL),
        make_result("row_count", "api", 50.0, MetricStatus.OK),
        make_result("latency", "api", 900.0, MetricStatus.CRITICAL),
    ]


def test_by_status_ok(sample_results):
    rf = ResultFilter(sample_results).by_status(MetricStatus.OK)
    assert len(rf) == 2
    assert all(r.status == MetricStatus.OK for r in rf.results())


def test_by_status_multiple(sample_results):
    rf = ResultFilter(sample_results).by_status(
        MetricStatus.WARNING, MetricStatus.CRITICAL
    )
    assert len(rf) == 3


def test_unhealthy(sample_results):
    rf = ResultFilter(sample_results).unhealthy()
    assert len(rf) == 3
    statuses = {r.status for r in rf.results()}
    assert MetricStatus.OK not in statuses


def test_by_source(sample_results):
    rf = ResultFilter(sample_results).by_source("api")
    assert len(rf) == 3
    assert all("api" in r.metric.source for r in rf.results())


def test_by_name(sample_results):
    rf = ResultFilter(sample_results).by_name("latency")
    assert len(rf) == 2
    assert all("latency" in r.metric.name for r in rf.results())


def test_above_value(sample_results):
    rf = ResultFilter(sample_results).above_value(300.0)
    assert len(rf) == 2
    assert all(r.value > 300.0 for r in rf.results())


def test_matching_predicate(sample_results):
    rf = ResultFilter(sample_results).matching(
        lambda r: r.metric.source == "warehouse" and r.status != MetricStatus.OK
    )
    assert len(rf) == 1
    assert rf.results()[0].metric.name == "latency"


def test_chaining(sample_results):
    rf = (
        ResultFilter(sample_results)
        .by_source("api")
        .by_status(MetricStatus.CRITICAL)
    )
    assert len(rf) == 2
    assert all(r.metric.source == "api" for r in rf.results())
    assert all(r.status == MetricStatus.CRITICAL for r in rf.results())


def test_empty_input():
    rf = ResultFilter([]).unhealthy()
    assert len(rf) == 0
    assert rf.results() == []


def test_repr(sample_results):
    rf = ResultFilter(sample_results)
    assert "5" in repr(rf)
