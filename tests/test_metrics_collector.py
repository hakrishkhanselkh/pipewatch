"""Tests for metrics evaluation and MetricCollector."""

import pytest

from pipewatch.metrics import Metric, MetricStatus, evaluate_metric
from pipewatch.collector import MetricCollector


def make_metric(name="row_count", value=100.0, source="db"):
    return Metric(name=name, value=value, source=source)


# --- evaluate_metric ---

def test_evaluate_ok_when_no_thresholds():
    result = evaluate_metric(make_metric(value=50.0))
    assert result.status == MetricStatus.OK


def test_evaluate_warning():
    result = evaluate_metric(make_metric(value=75.0), warning_threshold=70.0, critical_threshold=90.0)
    assert result.status == MetricStatus.WARNING


def test_evaluate_critical():
    result = evaluate_metric(make_metric(value=95.0), warning_threshold=70.0, critical_threshold=90.0)
    assert result.status == MetricStatus.CRITICAL


def test_evaluate_ok_below_warning():
    result = evaluate_metric(make_metric(value=50.0), warning_threshold=70.0)
    assert result.status == MetricStatus.OK
    assert result.is_healthy


# --- MetricCollector ---

def test_register_and_collect():
    collector = MetricCollector()
    collector.register_source("test", lambda: [make_metric(value=10.0)])
    results = collector.collect()
    assert len(results) == 1
    assert results[0].status == MetricStatus.OK


def test_register_duplicate_raises():
    collector = MetricCollector()
    collector.register_source("src", lambda: [])
    with pytest.raises(ValueError, match="already registered"):
        collector.register_source("src", lambda: [])


def test_thresholds_applied_during_collect():
    collector = MetricCollector()
    collector.register_source("src", lambda: [make_metric(name="latency", value=200.0)])
    collector.set_thresholds("latency", warning=100.0, critical=300.0)
    results = collector.collect()
    assert results[0].status == MetricStatus.WARNING


def test_source_exception_is_skipped():
    def bad_source():
        raise RuntimeError("connection failed")

    collector = MetricCollector()
    collector.register_source("bad", bad_source)
    results = collector.collect()
    assert results == []


def test_source_names():
    collector = MetricCollector()
    collector.register_source("alpha", lambda: [])
    collector.register_source("beta", lambda: [])
    assert set(collector.source_names) == {"alpha", "beta"}
