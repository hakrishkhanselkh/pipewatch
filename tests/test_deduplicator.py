"""Tests for pipewatch.deduplicator."""

from __future__ import annotations

import pytest

from pipewatch.deduplicator import Deduplicator, _result_fingerprint
from pipewatch.metrics import Metric, MetricResult, MetricStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    name: str = "row_count",
    source: str = "db",
    value: float = 100.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    metric = Metric(name=name, source=source, description="")
    return MetricResult(metric=metric, value=value, status=status)


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------

def test_fingerprint_differs_by_status():
    r_ok = make_result(status=MetricStatus.OK)
    r_warn = make_result(status=MetricStatus.WARNING)
    assert _result_fingerprint(r_ok) != _result_fingerprint(r_warn)


def test_fingerprint_differs_by_value():
    r1 = make_result(value=1.0)
    r2 = make_result(value=2.0)
    assert _result_fingerprint(r1) != _result_fingerprint(r2)


def test_fingerprint_same_for_identical_results():
    r1 = make_result()
    r2 = make_result()
    assert _result_fingerprint(r1) == _result_fingerprint(r2)


# ---------------------------------------------------------------------------
# Deduplicator.is_duplicate
# ---------------------------------------------------------------------------

def test_first_occurrence_is_not_duplicate():
    d = Deduplicator(window_seconds=60)
    result = make_result()
    assert d.is_duplicate(result, _now=0.0) is False


def test_second_occurrence_within_window_is_duplicate():
    d = Deduplicator(window_seconds=60)
    result = make_result()
    d.is_duplicate(result, _now=0.0)
    assert d.is_duplicate(result, _now=30.0) is True


def test_occurrence_after_window_is_not_duplicate():
    d = Deduplicator(window_seconds=60)
    result = make_result()
    d.is_duplicate(result, _now=0.0)
    assert d.is_duplicate(result, _now=61.0) is False


def test_different_results_are_independent():
    d = Deduplicator(window_seconds=60)
    r1 = make_result(name="a")
    r2 = make_result(name="b")
    d.is_duplicate(r1, _now=0.0)
    assert d.is_duplicate(r2, _now=1.0) is False


# ---------------------------------------------------------------------------
# Deduplicator.filter
# ---------------------------------------------------------------------------

def test_filter_removes_duplicates():
    d = Deduplicator(window_seconds=60)
    r = make_result()
    results = [r, r, r]
    filtered = d.filter(results, _now=0.0)
    assert len(filtered) == 1


def test_filter_keeps_distinct_results():
    d = Deduplicator(window_seconds=60)
    results = [make_result(name="a"), make_result(name="b"), make_result(name="c")]
    filtered = d.filter(results, _now=0.0)
    assert len(filtered) == 3


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def test_reset_clears_cache():
    d = Deduplicator(window_seconds=60)
    r = make_result()
    d.is_duplicate(r, _now=0.0)
    d.reset()
    assert len(d) == 0
    assert d.is_duplicate(r, _now=1.0) is False


def test_stats_tracks_counts():
    d = Deduplicator(window_seconds=60)
    r = make_result()
    d.is_duplicate(r, _now=0.0)
    d.is_duplicate(r, _now=5.0)
    d.is_duplicate(r, _now=10.0)
    counts = list(d.stats().values())
    assert counts == [3]


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        Deduplicator(window_seconds=0)
