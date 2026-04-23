"""Tests for pipewatch.ranker and the ResultRanker class."""

from __future__ import annotations

import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.ranker import RankedResult, ResultRanker


def make_result(
    name: str = "metric",
    source: str = "src",
    status: MetricStatus = MetricStatus.OK,
    value: float | None = 1.0,
) -> MetricResult:
    return MetricResult(source=source, name=name, value=value, status=status)


# ---------------------------------------------------------------------------
# RankedResult
# ---------------------------------------------------------------------------

def test_ranked_result_str():
    r = make_result(name="lag", source="kafka", status=MetricStatus.CRITICAL, value=99.0)
    ranked = RankedResult(result=r, rank=1)
    text = str(ranked)
    assert "[1]" in text
    assert "kafka/lag" in text
    assert "critical" in text


# ---------------------------------------------------------------------------
# ResultRanker — basic ordering
# ---------------------------------------------------------------------------

def test_critical_ranked_before_warning():
    ranker = ResultRanker([
        make_result(name="a", status=MetricStatus.WARNING, value=50.0),
        make_result(name="b", status=MetricStatus.CRITICAL, value=10.0),
    ])
    ranked = ranker.rank()
    assert ranked[0].result.name == "b"
    assert ranked[1].result.name == "a"


def test_warning_ranked_before_ok():
    ranker = ResultRanker([
        make_result(name="ok", status=MetricStatus.OK, value=5.0),
        make_result(name="warn", status=MetricStatus.WARNING, value=5.0),
    ])
    ranked = ranker.rank()
    assert ranked[0].result.name == "warn"


def test_same_status_sorted_by_value_descending():
    ranker = ResultRanker([
        make_result(name="low", status=MetricStatus.CRITICAL, value=10.0),
        make_result(name="high", status=MetricStatus.CRITICAL, value=90.0),
    ])
    ranked = ranker.rank()
    assert ranked[0].result.name == "high"
    assert ranked[1].result.name == "low"


def test_rank_positions_are_one_based():
    ranker = ResultRanker([
        make_result(name="x", status=MetricStatus.OK),
        make_result(name="y", status=MetricStatus.WARNING),
    ])
    ranked = ranker.rank()
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2


# ---------------------------------------------------------------------------
# ResultRanker — add / len / top
# ---------------------------------------------------------------------------

def test_add_increases_len():
    ranker = ResultRanker()
    assert len(ranker) == 0
    ranker.add(make_result())
    assert len(ranker) == 1


def test_top_returns_correct_number():
    results = [make_result(name=str(i), status=MetricStatus.OK, value=float(i)) for i in range(10)]
    ranker = ResultRanker(results)
    assert len(ranker.top(3)) == 3


def test_top_more_than_available_returns_all():
    ranker = ResultRanker([make_result()])
    assert len(ranker.top(100)) == 1


def test_none_value_handled_gracefully():
    ranker = ResultRanker([
        make_result(name="no_val", status=MetricStatus.WARNING, value=None),
        make_result(name="has_val", status=MetricStatus.WARNING, value=50.0),
    ])
    ranked = ranker.rank()
    assert ranked[0].result.name == "has_val"


def test_empty_ranker_returns_empty_list():
    ranker = ResultRanker()
    assert ranker.rank() == []
