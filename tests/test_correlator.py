"""Tests for pipewatch.correlator."""
import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.correlator import CorrelationGroup, CorrelationReport, ResultCorrelator


def make_result(
    name: str,
    source: str,
    status: MetricStatus = MetricStatus.OK,
    value: float = 1.0,
) -> MetricResult:
    return MetricResult(
        metric_name=name,
        source=source,
        value=value,
        status=status,
        timestamp=None,
    )


@pytest.fixture
def correlator() -> ResultCorrelator:
    return ResultCorrelator(min_sources=2)


def test_no_correlations_when_all_ok(correlator):
    correlator.add_all([
        make_result("latency", "src_a", MetricStatus.OK),
        make_result("latency", "src_b", MetricStatus.OK),
    ])
    report = correlator.correlate()
    assert not report.has_correlations
    assert report.groups == []


def test_single_source_failure_not_correlated(correlator):
    correlator.add(make_result("latency", "src_a", MetricStatus.WARNING))
    report = correlator.correlate()
    assert not report.has_correlations


def test_two_sources_same_metric_correlated(correlator):
    correlator.add_all([
        make_result("latency", "src_a", MetricStatus.WARNING),
        make_result("latency", "src_b", MetricStatus.WARNING),
    ])
    report = correlator.correlate()
    assert report.has_correlations
    assert len(report.groups) == 1
    assert report.groups[0].metric_name == "latency"
    assert report.groups[0].source_count == 2


def test_dominant_status_is_critical_when_mixed(correlator):
    correlator.add_all([
        make_result("error_rate", "src_a", MetricStatus.WARNING),
        make_result("error_rate", "src_b", MetricStatus.CRITICAL),
    ])
    report = correlator.correlate()
    assert report.groups[0].status == MetricStatus.CRITICAL


def test_dominant_status_warning_when_all_warning(correlator):
    correlator.add_all([
        make_result("throughput", "src_a", MetricStatus.WARNING),
        make_result("throughput", "src_b", MetricStatus.WARNING),
    ])
    report = correlator.correlate()
    assert report.groups[0].status == MetricStatus.WARNING


def test_by_metric_returns_correct_group(correlator):
    correlator.add_all([
        make_result("latency", "src_a", MetricStatus.WARNING),
        make_result("latency", "src_b", MetricStatus.WARNING),
    ])
    report = correlator.correlate()
    group = report.by_metric("latency")
    assert group is not None
    assert group.metric_name == "latency"


def test_by_metric_returns_none_for_unknown(correlator):
    report = correlator.correlate()
    assert report.by_metric("nonexistent") is None


def test_clear_removes_all_results(correlator):
    correlator.add_all([
        make_result("latency", "src_a", MetricStatus.CRITICAL),
        make_result("latency", "src_b", MetricStatus.CRITICAL),
    ])
    correlator.clear()
    report = correlator.correlate()
    assert not report.has_correlations


def test_min_sources_validation():
    with pytest.raises(ValueError):
        ResultCorrelator(min_sources=0)


def test_str_no_correlations(correlator):
    report = correlator.correlate()
    assert "no correlated" in str(report)


def test_str_with_correlations(correlator):
    correlator.add_all([
        make_result("latency", "src_a", MetricStatus.WARNING),
        make_result("latency", "src_b", MetricStatus.WARNING),
    ])
    report = correlator.correlate()
    text = str(report)
    assert "1 group" in text
    assert "latency" in text


def test_correlation_group_str():
    results = [
        make_result("cpu", "src_a", MetricStatus.CRITICAL),
        make_result("cpu", "src_b", MetricStatus.CRITICAL),
    ]
    group = CorrelationGroup(metric_name="cpu", status=MetricStatus.CRITICAL, results=results)
    text = str(group)
    assert "cpu" in text
    assert "critical" in text.lower()
