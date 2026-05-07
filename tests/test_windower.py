"""Tests for pipewatch.windower."""
from datetime import datetime, timedelta

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.windower import ResultWindower, WindowConfig, WindowStats


def make_result(
    source: str = "src",
    name: str = "latency",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
    ts: datetime | None = None,
) -> MetricResult:
    m = Metric(source=source, name=name)
    return MetricResult(
        metric=m,
        value=value,
        status=status,
        timestamp=ts or datetime.utcnow(),
    )


# --- WindowConfig ---

def test_config_default_window():
    cfg = WindowConfig()
    assert cfg.window_seconds == 60.0


def test_config_rejects_zero_window():
    with pytest.raises(ValueError):
        WindowConfig(window_seconds=0)


def test_config_rejects_negative_window():
    with pytest.raises(ValueError):
        WindowConfig(window_seconds=-5)


def test_config_rejects_zero_max_entries():
    with pytest.raises(ValueError):
        WindowConfig(max_entries=0)


# --- ResultWindower ---

def test_stats_empty_when_no_results():
    w = ResultWindower()
    s = w.stats("src", "latency")
    assert s.count == 0
    assert s.avg_value is None


def test_add_and_stats_basic():
    w = ResultWindower()
    w.add(make_result(value=10.0, status=MetricStatus.OK))
    w.add(make_result(value=20.0, status=MetricStatus.WARNING))
    s = w.stats("src", "latency")
    assert s.count == 2
    assert s.avg_value == pytest.approx(15.0)
    assert s.ok_count == 1
    assert s.warning_count == 1
    assert s.critical_count == 0


def test_evicts_old_results():
    cfg = WindowConfig(window_seconds=10)
    w = ResultWindower(cfg)
    old_ts = datetime.utcnow() - timedelta(seconds=30)
    w.add(make_result(value=99.0, ts=old_ts))
    w.add(make_result(value=1.0, ts=datetime.utcnow()))
    s = w.stats("src", "latency")
    assert s.count == 1
    assert s.avg_value == pytest.approx(1.0)


def test_all_stats_returns_all_keys():
    w = ResultWindower()
    w.add(make_result(source="a", name="x"))
    w.add(make_result(source="b", name="y"))
    keys = {(s.source, s.name) for s in w.all_stats()}
    assert ("a", "x") in keys
    assert ("b", "y") in keys


def test_clear_removes_all_entries():
    w = ResultWindower()
    w.add(make_result())
    w.clear()
    assert w.all_stats() == []


def test_window_stats_str_with_data():
    w = ResultWindower()
    w.add(make_result(value=5.0))
    s = w.stats("src", "latency")
    text = str(s)
    assert "src/latency" in text
    assert "count=1" in text


def test_window_stats_str_empty():
    w = ResultWindower()
    s = w.stats("src", "latency")
    text = str(s)
    assert "count=0" in text


def test_min_max_values():
    w = ResultWindower()
    for v in [3.0, 7.0, 1.0, 5.0]:
        w.add(make_result(value=v))
    s = w.stats("src", "latency")
    assert s.min_value == pytest.approx(1.0)
    assert s.max_value == pytest.approx(7.0)
