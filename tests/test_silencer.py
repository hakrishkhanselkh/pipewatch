"""Tests for pipewatch.silencer."""

import time

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.silencer import Silencer, SilenceRule


def make_result(
    source: str = "src",
    name: str = "latency",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.WARNING,
) -> MetricResult:
    metric = Metric(name=name, value=value)
    return MetricResult(metric=metric, status=status, source=source)


# ---------------------------------------------------------------------------
# SilenceRule
# ---------------------------------------------------------------------------

def test_rule_matches_source_and_metric():
    rule = SilenceRule(source="src", metric_name="latency")
    result = make_result(source="src", name="latency")
    assert rule.matches(result)


def test_rule_does_not_match_wrong_source():
    rule = SilenceRule(source="other", metric_name="latency")
    result = make_result(source="src", name="latency")
    assert not rule.matches(result)


def test_rule_does_not_match_wrong_metric():
    rule = SilenceRule(source="src", metric_name="throughput")
    result = make_result(source="src", name="latency")
    assert not rule.matches(result)


def test_rule_with_only_source_matches_any_metric():
    rule = SilenceRule(source="src")
    r1 = make_result(source="src", name="latency")
    r2 = make_result(source="src", name="errors")
    assert rule.matches(r1)
    assert rule.matches(r2)


def test_rule_with_only_metric_matches_any_source():
    rule = SilenceRule(metric_name="latency")
    r1 = make_result(source="a", name="latency")
    r2 = make_result(source="b", name="latency")
    assert rule.matches(r1)
    assert rule.matches(r2)


def test_expired_rule_does_not_match():
    rule = SilenceRule(source="src", expires_at=time.time() - 1)
    result = make_result(source="src")
    assert not rule.matches(result)


def test_rule_str_includes_source_and_metric():
    rule = SilenceRule(source="db", metric_name="lag", reason="maintenance")
    text = str(rule)
    assert "source='db'" in text
    assert "metric='lag'" in text
    assert "reason='maintenance'" in text


# ---------------------------------------------------------------------------
# Silencer
# ---------------------------------------------------------------------------

def test_no_rules_means_not_silenced():
    silencer = Silencer()
    assert not silencer.is_silenced(make_result())


def test_matching_rule_silences_result():
    silencer = Silencer()
    silencer.add_rule(SilenceRule(source="src", metric_name="latency"))
    assert silencer.is_silenced(make_result(source="src", name="latency"))


def test_non_matching_rule_does_not_silence():
    silencer = Silencer()
    silencer.add_rule(SilenceRule(source="other"))
    assert not silencer.is_silenced(make_result(source="src"))


def test_expired_rule_purged_from_active():
    silencer = Silencer()
    silencer.add_rule(SilenceRule(source="src", expires_at=time.time() - 1))
    assert len(silencer.active_rules()) == 0
    assert len(silencer) == 0


def test_clear_removes_all_rules():
    silencer = Silencer()
    silencer.add_rule(SilenceRule(source="src"))
    silencer.add_rule(SilenceRule(metric_name="lag"))
    silencer.clear()
    assert len(silencer) == 0


def test_len_counts_active_rules():
    silencer = Silencer()
    silencer.add_rule(SilenceRule(source="a"))
    silencer.add_rule(SilenceRule(source="b", expires_at=time.time() - 1))
    assert len(silencer) == 1
