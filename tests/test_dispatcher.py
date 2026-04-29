"""Tests for pipewatch.dispatcher."""

from __future__ import annotations

from datetime import datetime
from typing import List

import pytest

from pipewatch.dispatcher import DispatchReport, ResultDispatcher
from pipewatch.metrics import MetricResult, MetricStatus


def make_result(
    name: str = "lag",
    source: str = "kafka",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        name=name,
        source=source,
        value=value,
        status=status,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# DispatchReport
# ---------------------------------------------------------------------------

def test_report_success_when_no_errors():
    r = DispatchReport(total=3, handler_count=2)
    assert r.success is True


def test_report_failure_when_errors_present():
    r = DispatchReport(total=1, handler_count=1, errors=["[h] ValueError: bad"])
    assert r.success is False


def test_report_str_contains_status():
    r = DispatchReport(total=5, handler_count=3)
    assert "OK" in str(r)
    assert "5" in str(r)


# ---------------------------------------------------------------------------
# ResultDispatcher – registration
# ---------------------------------------------------------------------------

def test_register_adds_handler():
    d = ResultDispatcher()
    d.register("a", lambda r: None)
    assert "a" in d.handler_names


def test_register_non_callable_raises():
    d = ResultDispatcher()
    with pytest.raises(TypeError):
        d.register("bad", "not_a_function")  # type: ignore[arg-type]


def test_unregister_returns_true_when_found():
    d = ResultDispatcher()
    d.register("x", lambda r: None)
    assert d.unregister("x") is True
    assert "x" not in d.handler_names


def test_unregister_returns_false_when_missing():
    d = ResultDispatcher()
    assert d.unregister("ghost") is False


# ---------------------------------------------------------------------------
# ResultDispatcher – dispatch
# ---------------------------------------------------------------------------

def test_dispatch_calls_all_handlers_for_each_result():
    received: List[MetricResult] = []
    d = ResultDispatcher()
    d.register("collector", received.append)

    results = [make_result(name=f"m{i}") for i in range(3)]
    report = d.dispatch(results)

    assert len(received) == 3
    assert report.total == 3
    assert report.success is True


def test_dispatch_fan_out_to_multiple_handlers():
    bucket_a: List[MetricResult] = []
    bucket_b: List[MetricResult] = []
    d = ResultDispatcher()
    d.register("a", bucket_a.append)
    d.register("b", bucket_b.append)

    d.dispatch([make_result()])

    assert len(bucket_a) == 1
    assert len(bucket_b) == 1


def test_dispatch_captures_handler_errors():
    def bad_handler(r: MetricResult) -> None:
        raise RuntimeError("boom")

    d = ResultDispatcher()
    d.register("broken", bad_handler)

    report = d.dispatch([make_result()])

    assert not report.success
    assert len(report.errors) == 1
    assert "broken" in report.errors[0]


def test_dispatch_continues_after_error():
    """A failing handler must not prevent subsequent handlers from running."""
    received: List[MetricResult] = []
    d = ResultDispatcher()
    d.register("bad", lambda r: (_ for _ in ()).throw(ValueError("oops")))
    d.register("good", received.append)

    d.dispatch([make_result()])

    assert len(received) == 1


def test_dispatch_empty_results_returns_zero_total():
    d = ResultDispatcher()
    d.register("noop", lambda r: None)
    report = d.dispatch([])
    assert report.total == 0
    assert report.success is True
