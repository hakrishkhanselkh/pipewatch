"""Tests for pipewatch.aggregator and cli_aggregate."""

from __future__ import annotations

import json
import pytest

from pipewatch.aggregator import AggregatedStats, ResultAggregator
from pipewatch.metrics import Metric, MetricResult, MetricStatus


def make_result(
    name: str = "latency",
    source: str = "db",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    m = Metric(name=name, source=source, value=value)
    return MetricResult(metric=m, value=value, status=status)


class TestResultAggregator:
    def test_stats_none_when_empty(self):
        agg = ResultAggregator()
        assert agg.stats("db", "latency") is None

    def test_single_result_stats(self):
        agg = ResultAggregator()
        agg.add(make_result(value=5.0))
        s = agg.stats("db", "latency")
        assert s is not None
        assert s.count == 1
        assert s.mean == pytest.approx(5.0)
        assert s.minimum == pytest.approx(5.0)
        assert s.maximum == pytest.approx(5.0)
        assert s.latest_status == MetricStatus.OK

    def test_multiple_results_aggregated(self):
        agg = ResultAggregator()
        agg.add(make_result(value=2.0))
        agg.add(make_result(value=4.0))
        agg.add(make_result(value=6.0))
        s = agg.stats("db", "latency")
        assert s.count == 3
        assert s.mean == pytest.approx(4.0)
        assert s.minimum == pytest.approx(2.0)
        assert s.maximum == pytest.approx(6.0)

    def test_latest_status_reflects_last_added(self):
        agg = ResultAggregator()
        agg.add(make_result(value=1.0, status=MetricStatus.OK))
        agg.add(make_result(value=9.0, status=MetricStatus.CRITICAL))
        s = agg.stats("db", "latency")
        assert s.latest_status == MetricStatus.CRITICAL

    def test_add_many(self):
        agg = ResultAggregator()
        results = [make_result(value=float(i)) for i in range(5)]
        agg.add_many(results)
        s = agg.stats("db", "latency")
        assert s.count == 5

    def test_all_stats_returns_all_keys(self):
        agg = ResultAggregator()
        agg.add(make_result(name="latency", source="db", value=1.0))
        agg.add(make_result(name="errors", source="api", value=2.0))
        keys = {(s.source, s.name) for s in agg.all_stats()}
        assert ("db", "latency") in keys
        assert ("api", "errors") in keys

    def test_clear_removes_data(self):
        agg = ResultAggregator()
        agg.add(make_result(value=1.0))
        agg.clear()
        assert agg.stats("db", "latency") is None
        assert agg.all_stats() == []

    def test_str_representation(self):
        s = AggregatedStats(
            source="db",
            name="latency",
            count=3,
            mean=4.0,
            minimum=2.0,
            maximum=6.0,
            latest_status=MetricStatus.WARNING,
        )
        text = str(s)
        assert "db/latency" in text
        assert "warning" in text
        assert "count=3" in text
