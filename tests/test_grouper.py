"""Tests for pipewatch.grouper."""
from __future__ import annotations

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.grouper import GroupSummary, ResultGrouper


def make_result(
    source: str = "src",
    name: str = "metric",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    metric = Metric(name=name, source=source)
    return MetricResult(metric=metric, value=value, status=status)


# ---------------------------------------------------------------------------
# GroupSummary unit tests
# ---------------------------------------------------------------------------

def test_empty_group_summary():
    gs = GroupSummary(key="k")
    assert gs.count == 0
    assert gs.worst_status == MetricStatus.OK


def test_group_summary_counts():
    gs = GroupSummary(key="k", results=[
        make_result(status=MetricStatus.OK),
        make_result(status=MetricStatus.WARNING),
        make_result(status=MetricStatus.CRITICAL),
        make_result(status=MetricStatus.OK),
    ])
    assert gs.ok_count == 2
    assert gs.warning_count == 1
    assert gs.critical_count == 1
    assert gs.count == 4


def test_worst_status_critical_takes_priority():
    gs = GroupSummary(key="k", results=[
        make_result(status=MetricStatus.WARNING),
        make_result(status=MetricStatus.CRITICAL),
    ])
    assert gs.worst_status == MetricStatus.CRITICAL


def test_worst_status_warning_when_no_critical():
    gs = GroupSummary(key="k", results=[
        make_result(status=MetricStatus.OK),
        make_result(status=MetricStatus.WARNING),
    ])
    assert gs.worst_status == MetricStatus.WARNING


def test_group_summary_str_contains_key():
    gs = GroupSummary(key="my_group")
    assert "my_group" in str(gs)


# ---------------------------------------------------------------------------
# ResultGrouper unit tests
# ---------------------------------------------------------------------------

def test_grouper_len_zero_initially():
    g = ResultGrouper(key_fn=lambda r: r.metric.source)
    assert len(g) == 0


def test_grouper_by_source():
    g = ResultGrouper(key_fn=lambda r: r.metric.source)
    g.add(make_result(source="a"))
    g.add(make_result(source="b"))
    g.add(make_result(source="a"))
    assert len(g) == 2
    assert g.get("a").count == 2
    assert g.get("b").count == 1


def test_grouper_by_status():
    g = ResultGrouper(key_fn=lambda r: r.status.value)
    g.add_all([
        make_result(status=MetricStatus.OK),
        make_result(status=MetricStatus.CRITICAL),
        make_result(status=MetricStatus.OK),
    ])
    assert g.get("ok").count == 2
    assert g.get("critical").count == 1


def test_grouper_get_unknown_returns_none():
    g = ResultGrouper(key_fn=lambda r: r.metric.source)
    assert g.get("nonexistent") is None


def test_grouper_all_groups_returns_all():
    g = ResultGrouper(key_fn=lambda r: r.metric.source)
    g.add(make_result(source="x"))
    g.add(make_result(source="y"))
    keys = {gs.key for gs in g.all_groups()}
    assert keys == {"x", "y"}


def test_grouper_keys():
    g = ResultGrouper(key_fn=lambda r: r.metric.name)
    g.add(make_result(name="latency"))
    g.add(make_result(name="error_rate"))
    assert set(g.keys()) == {"latency", "error_rate"}
