"""Tests for pipewatch.trimmer."""
import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.trimmer import TrimConfig, TrimReport, ResultTrimmer


def make_result(
    name: str = "latency",
    source: str = "db",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        metric_name=name,
        source=source,
        value=value,
        status=status,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# TrimConfig
# ---------------------------------------------------------------------------

def test_config_accepts_valid_bounds():
    cfg = TrimConfig(min_value=0.0, max_value=100.0)
    assert cfg.min_value == 0.0
    assert cfg.max_value == 100.0


def test_config_accepts_none_bounds():
    cfg = TrimConfig()
    assert cfg.min_value is None
    assert cfg.max_value is None


def test_config_rejects_inverted_bounds():
    with pytest.raises(ValueError, match="min_value"):
        TrimConfig(min_value=50.0, max_value=10.0)


def test_config_accepts_equal_bounds():
    # edge case: min == max is allowed (keeps only exact matches)
    cfg = TrimConfig(min_value=5.0, max_value=5.0)
    assert cfg.min_value == cfg.max_value


# ---------------------------------------------------------------------------
# ResultTrimmer
# ---------------------------------------------------------------------------

def test_empty_results_produce_empty_report():
    trimmer = ResultTrimmer(TrimConfig(min_value=0.0, max_value=100.0))
    report = trimmer.trim([])
    assert report.kept_count == 0
    assert report.removed_count == 0


def test_all_within_range_are_kept():
    trimmer = ResultTrimmer(TrimConfig(min_value=0.0, max_value=100.0))
    results = [make_result(value=v) for v in (0.0, 50.0, 100.0)]
    report = trimmer.trim(results)
    assert report.kept_count == 3
    assert report.removed_count == 0


def test_below_min_is_removed():
    trimmer = ResultTrimmer(TrimConfig(min_value=10.0))
    results = [make_result(value=5.0), make_result(value=15.0)]
    report = trimmer.trim(results)
    assert report.removed_count == 1
    assert report.removed[0].value == 5.0


def test_above_max_is_removed():
    trimmer = ResultTrimmer(TrimConfig(max_value=20.0))
    results = [make_result(value=25.0), make_result(value=10.0)]
    report = trimmer.trim(results)
    assert report.removed_count == 1
    assert report.removed[0].value == 25.0


def test_none_value_is_always_kept():
    trimmer = ResultTrimmer(TrimConfig(min_value=0.0, max_value=1.0))
    result = make_result(value=None)
    report = trimmer.trim([result])
    assert report.kept_count == 1
    assert report.removed_count == 0


def test_no_bounds_keeps_everything():
    trimmer = ResultTrimmer(TrimConfig())
    results = [make_result(value=v) for v in (-999.0, 0.0, 999.0)]
    report = trimmer.trim(results)
    assert report.kept_count == 3


def test_trim_report_str():
    report = TrimReport(kept=[make_result()], removed=[])
    assert "kept=1" in str(report)
    assert "removed=0" in str(report)
