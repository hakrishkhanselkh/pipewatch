"""Tests for pipewatch.normalizer."""
import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.normalizer import NormalizerConfig, NormalizedResult, ResultNormalizer


def make_result(
    name: str = "latency",
    value: float = 0.0,
    source: str = "src",
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        name=name,
        source=source,
        value=value,
        status=status,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# NormalizerConfig
# ---------------------------------------------------------------------------

def test_config_rejects_equal_bounds():
    with pytest.raises(ValueError):
        NormalizerConfig(min_value=5.0, max_value=5.0)


def test_config_rejects_inverted_bounds():
    with pytest.raises(ValueError):
        NormalizerConfig(min_value=10.0, max_value=1.0)


def test_config_accepts_valid_bounds():
    cfg = NormalizerConfig(min_value=0.0, max_value=100.0)
    assert cfg.min_value == 0.0
    assert cfg.max_value == 100.0


# ---------------------------------------------------------------------------
# ResultNormalizer
# ---------------------------------------------------------------------------

def test_no_config_returns_none_normalized():
    normalizer = ResultNormalizer()
    result = make_result(name="latency", value=50.0)
    nr = normalizer.normalize_one(result)
    assert nr.normalized_value is None


def test_midpoint_normalizes_to_half():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(min_value=0.0, max_value=200.0))
    nr = normalizer.normalize_one(make_result(name="latency", value=100.0))
    assert nr.normalized_value == pytest.approx(0.5)


def test_min_value_normalizes_to_zero():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(min_value=10.0, max_value=110.0))
    nr = normalizer.normalize_one(make_result(name="latency", value=10.0))
    assert nr.normalized_value == pytest.approx(0.0)


def test_max_value_normalizes_to_one():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(min_value=10.0, max_value=110.0))
    nr = normalizer.normalize_one(make_result(name="latency", value=110.0))
    assert nr.normalized_value == pytest.approx(1.0)


def test_value_below_min_clamps_to_zero():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(min_value=50.0, max_value=150.0))
    nr = normalizer.normalize_one(make_result(name="latency", value=0.0))
    assert nr.normalized_value == pytest.approx(0.0)


def test_value_above_max_clamps_to_one():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(min_value=0.0, max_value=100.0))
    nr = normalizer.normalize_one(make_result(name="latency", value=999.0))
    assert nr.normalized_value == pytest.approx(1.0)


def test_none_value_returns_none_normalized():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(min_value=0.0, max_value=100.0))
    result = make_result(name="latency", value=0.0)
    result = MetricResult(
        name=result.name,
        source=result.source,
        value=None,
        status=result.status,
        timestamp=None,
    )
    nr = normalizer.normalize_one(result)
    assert nr.normalized_value is None


def test_normalize_list_returns_correct_length():
    normalizer = ResultNormalizer()
    normalizer.register("cpu", NormalizerConfig(min_value=0.0, max_value=100.0))
    results = [make_result(name="cpu", value=float(v)) for v in range(5)]
    normalized = normalizer.normalize(results)
    assert len(normalized) == 5


def test_registered_metrics_sorted():
    normalizer = ResultNormalizer()
    normalizer.register("z_metric", NormalizerConfig(0.0, 1.0))
    normalizer.register("a_metric", NormalizerConfig(0.0, 1.0))
    normalizer.register("m_metric", NormalizerConfig(0.0, 1.0))
    assert normalizer.registered_metrics == ["a_metric", "m_metric", "z_metric"]


def test_normalized_result_str_contains_normalized_value():
    normalizer = ResultNormalizer()
    normalizer.register("latency", NormalizerConfig(0.0, 100.0))
    nr = normalizer.normalize_one(make_result(name="latency", value=25.0))
    s = str(nr)
    assert "0.2500" in s
    assert "latency" in s


def test_normalized_result_str_na_when_no_config():
    normalizer = ResultNormalizer()
    nr = normalizer.normalize_one(make_result(name="unknown", value=10.0))
    assert "n/a" in str(nr)
