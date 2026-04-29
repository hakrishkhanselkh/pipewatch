"""Tests for pipewatch.reaper."""

from datetime import datetime, timedelta, timezone

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.reaper import ReaperConfig, ReapReport, ResultReaper


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_result(
    name: str = "latency",
    source: str = "db",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
    age_seconds: float | None = 0.0,
) -> MetricResult:
    ts = None if age_seconds is None else (NOW - timedelta(seconds=age_seconds))
    return MetricResult(
        metric=Metric(name=name, source=source),
        value=value,
        status=status,
        timestamp=ts,
    )


def make_reaper(max_age: float = 3600.0) -> ResultReaper:
    config = ReaperConfig(max_age_seconds=max_age, now=NOW)
    return ResultReaper(config)


# --- ReaperConfig ---

def test_config_rejects_zero_max_age():
    with pytest.raises(ValueError):
        ReaperConfig(max_age_seconds=0)


def test_config_rejects_negative_max_age():
    with pytest.raises(ValueError):
        ReaperConfig(max_age_seconds=-10)


def test_config_accepts_valid_max_age():
    cfg = ReaperConfig(max_age_seconds=60)
    assert cfg.max_age_seconds == 60


# --- ResultReaper.reap ---

def test_fresh_result_is_kept():
    reaper = make_reaper(max_age=3600)
    r = make_result(age_seconds=100)
    report = reaper.reap([r])
    assert report.kept_count == 1
    assert report.removed_count == 0


def test_stale_result_is_removed():
    reaper = make_reaper(max_age=3600)
    r = make_result(age_seconds=7200)
    report = reaper.reap([r])
    assert report.kept_count == 0
    assert report.removed_count == 1


def test_result_exactly_at_cutoff_is_kept():
    reaper = make_reaper(max_age=3600)
    r = make_result(age_seconds=3600)
    report = reaper.reap([r])
    assert report.kept_count == 1


def test_none_timestamp_is_kept():
    reaper = make_reaper(max_age=3600)
    r = make_result(age_seconds=None)
    report = reaper.reap([r])
    assert report.kept_count == 1


def test_mixed_results_partitioned_correctly():
    reaper = make_reaper(max_age=3600)
    fresh = make_result(name="a", age_seconds=60)
    stale = make_result(name="b", age_seconds=9000)
    report = reaper.reap([fresh, stale])
    assert report.kept_count == 1
    assert report.removed_count == 1
    assert report.kept[0].metric.name == "a"
    assert report.removed[0].metric.name == "b"


def test_empty_input_returns_empty_report():
    reaper = make_reaper()
    report = reaper.reap([])
    assert report.kept_count == 0
    assert report.removed_count == 0


def test_report_str_contains_counts():
    report = ReapReport(kept=[], removed=[])
    assert "kept=0" in str(report)
    assert "removed=0" in str(report)
