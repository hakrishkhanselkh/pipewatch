"""Tests for pipewatch.throttler."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.throttler import ThrottleConfig, Throttler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    source: str = "src",
    name: str = "latency",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(source=source, name=name, value=value, status=status)


# ---------------------------------------------------------------------------
# ThrottleConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    cfg = ThrottleConfig()
    assert cfg.max_per_window == 10
    assert cfg.window_seconds == 60.0


def test_config_rejects_zero_max():
    with pytest.raises(ValueError, match="max_per_window"):
        ThrottleConfig(max_per_window=0)


def test_config_rejects_negative_window():
    with pytest.raises(ValueError, match="window_seconds"):
        ThrottleConfig(window_seconds=-1.0)


# ---------------------------------------------------------------------------
# Throttler.filter
# ---------------------------------------------------------------------------

def test_all_allowed_below_limit():
    throttler = Throttler(ThrottleConfig(max_per_window=5, window_seconds=60))
    results = [make_result() for _ in range(4)]
    allowed = throttler.filter(results)
    assert len(allowed) == 4
    assert throttler.dropped_count("src") == 0


def test_excess_results_are_dropped():
    throttler = Throttler(ThrottleConfig(max_per_window=3, window_seconds=60))
    results = [make_result() for _ in range(6)]
    allowed = throttler.filter(results)
    assert len(allowed) == 3
    assert throttler.dropped_count("src") == 3


def test_different_sources_have_independent_limits():
    throttler = Throttler(ThrottleConfig(max_per_window=2, window_seconds=60))
    results = [
        make_result(source="a"),
        make_result(source="a"),
        make_result(source="a"),  # this one should be dropped
        make_result(source="b"),
        make_result(source="b"),
    ]
    allowed = throttler.filter(results)
    assert len(allowed) == 4
    assert throttler.dropped_count("a") == 1
    assert throttler.dropped_count("b") == 0


def test_results_allowed_after_window_expires():
    throttler = Throttler(ThrottleConfig(max_per_window=2, window_seconds=1.0))
    results = [make_result() for _ in range(2)]
    throttler.filter(results)
    # Advance time beyond the window
    time.sleep(1.1)
    new_results = [make_result() for _ in range(2)]
    allowed = throttler.filter(new_results)
    assert len(allowed) == 2


def test_reset_clears_single_source():
    throttler = Throttler(ThrottleConfig(max_per_window=1, window_seconds=60))
    throttler.filter([make_result(source="x"), make_result(source="x")])
    assert throttler.dropped_count("x") == 1
    throttler.reset("x")
    assert throttler.dropped_count("x") == 0
    # After reset, window is cleared so next call should be allowed
    allowed = throttler.filter([make_result(source="x")])
    assert len(allowed) == 1


def test_reset_all_clears_everything():
    throttler = Throttler(ThrottleConfig(max_per_window=1, window_seconds=60))
    throttler.filter([make_result(source="a"), make_result(source="b")])
    throttler.reset()
    assert throttler.dropped_count("a") == 0
    assert throttler.dropped_count("b") == 0


def test_dropped_count_unknown_source_returns_zero():
    throttler = Throttler()
    assert throttler.dropped_count("never_seen") == 0


def test_empty_input_returns_empty():
    throttler = Throttler()
    assert throttler.filter([]) == []
