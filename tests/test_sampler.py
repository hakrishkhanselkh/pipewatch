"""Tests for pipewatch.sampler."""

from __future__ import annotations

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.sampler import ResultSampler, SamplerConfig


def make_result(
    name: str = "latency",
    source: str = "db",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    metric = Metric(name=name, source=source)
    return MetricResult(metric=metric, value=value, status=status)


# ---------------------------------------------------------------------------
# SamplerConfig validation
# ---------------------------------------------------------------------------

def test_config_default_rate_is_one():
    cfg = SamplerConfig()
    assert cfg.rate == 1.0


def test_config_rejects_zero_rate():
    with pytest.raises(ValueError, match="rate"):
        SamplerConfig(rate=0.0)


def test_config_rejects_negative_rate():
    with pytest.raises(ValueError):
        SamplerConfig(rate=-0.5)


def test_config_rejects_rate_above_one():
    with pytest.raises(ValueError):
        SamplerConfig(rate=1.1)


# ---------------------------------------------------------------------------
# Sampling behaviour
# ---------------------------------------------------------------------------

def test_rate_one_keeps_all():
    results = [make_result(name=f"m{i}") for i in range(20)]
    sampler = ResultSampler(SamplerConfig(rate=1.0))
    report = sampler.sample(results)
    assert report.kept == 20
    assert report.dropped == 0
    assert report.total == 20


def test_critical_always_kept_regardless_of_rate():
    critical = make_result(name="err", status=MetricStatus.CRITICAL)
    ok_results = [make_result(name=f"ok{i}") for i in range(100)]
    # rate=0.01 means almost nothing passes, but CRITICAL must survive
    sampler = ResultSampler(SamplerConfig(rate=0.01, seed=42))
    report = sampler.sample([critical] + ok_results)
    assert critical in report.results


def test_sample_report_str_contains_fraction():
    results = [make_result(name=f"m{i}") for i in range(10)]
    sampler = ResultSampler(SamplerConfig(rate=1.0))
    report = sampler.sample(results)
    text = str(report)
    assert "10/10" in text
    assert "100.0%" in text


def test_empty_input_returns_zero_counts():
    sampler = ResultSampler()
    report = sampler.sample([])
    assert report.total == 0
    assert report.kept == 0
    assert report.dropped == 0


def test_seeded_sampler_is_deterministic():
    results = [make_result(name=f"m{i}") for i in range(50)]
    cfg = SamplerConfig(rate=0.5, seed=7)
    report_a = ResultSampler(cfg).sample(results)
    report_b = ResultSampler(cfg).sample(results)
    assert [r.metric.name for r in report_a.results] == [
        r.metric.name for r in report_b.results
    ]


def test_warning_not_in_always_keep_by_default():
    """WARNING results should be subject to normal sampling at low rates."""
    warnings = [make_result(name=f"w{i}", status=MetricStatus.WARNING) for i in range(200)]
    sampler = ResultSampler(SamplerConfig(rate=0.01, seed=0))
    report = sampler.sample(warnings)
    # With rate=0.01 and 200 items, expect far fewer than 200 kept
    assert report.kept < 50
