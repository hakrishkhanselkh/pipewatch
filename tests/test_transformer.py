"""Tests for pipewatch.transformer."""

from __future__ import annotations

from dataclasses import replace
from typing import List

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.transformer import ResultTransformer, TransformReport, TransformRule


def make_result(
    source: str = "src",
    name: str = "latency",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        metric=Metric(source=source, name=name),
        value=value,
        status=status,
    )


# ---------------------------------------------------------------------------
# TransformRule
# ---------------------------------------------------------------------------

class TestTransformRule:
    def test_applies_to_uses_predicate(self):
        rule = TransformRule(
            name="only-src-a",
            predicate=lambda r: r.metric.source == "a",
            transform=lambda r: r,
        )
        assert rule.applies_to(make_result(source="a"))
        assert not rule.applies_to(make_result(source="b"))

    def test_str_contains_name(self):
        rule = TransformRule("my-rule", lambda r: True, lambda r: r)
        assert "my-rule" in str(rule)

    def test_apply_invokes_transform(self):
        rule = TransformRule(
            name="zero-value",
            predicate=lambda r: True,
            transform=lambda r: replace(r, value=0.0),
        )
        result = make_result(value=42.0)
        assert rule.apply(result).value == 0.0


# ---------------------------------------------------------------------------
# TransformReport
# ---------------------------------------------------------------------------

class TestTransformReport:
    def test_str_contains_counts(self):
        report = TransformReport(total=10, transformed=3, rules_applied=["r1"])
        s = str(report)
        assert "10" in s
        assert "3" in s
        assert "r1" in s


# ---------------------------------------------------------------------------
# ResultTransformer
# ---------------------------------------------------------------------------

class TestResultTransformer:
    def _make_transformer(self) -> ResultTransformer:
        return ResultTransformer()

    def test_empty_rules_returns_unchanged(self):
        t = self._make_transformer()
        results = [make_result(value=5.0), make_result(value=3.0)]
        out, report = t.transform(results)
        assert [r.value for r in out] == [5.0, 3.0]
        assert report.transformed == 0
        assert report.total == 2

    def test_clamp_negative_rule(self):
        t = self._make_transformer()
        t.add_rule(
            TransformRule(
                "clamp",
                lambda r: True,
                lambda r: replace(r, value=max(0.0, r.value)) if r.value is not None else r,
            )
        )
        results = [make_result(value=-5.0), make_result(value=3.0)]
        out, report = t.transform(results)
        assert out[0].value == 0.0
        assert out[1].value == 3.0
        assert report.transformed == 1
        assert "clamp" in report.rules_applied

    def test_rule_count(self):
        t = self._make_transformer()
        assert t.rule_count() == 0
        t.add_rule(TransformRule("r", lambda r: True, lambda r: r))
        assert t.rule_count() == 1

    def test_multiple_rules_applied_in_order(self):
        t = self._make_transformer()
        t.add_rule(TransformRule("double", lambda r: True, lambda r: replace(r, value=r.value * 2)))
        t.add_rule(TransformRule("add10", lambda r: True, lambda r: replace(r, value=r.value + 10)))
        results = [make_result(value=5.0)]
        out, _ = t.transform(results)
        assert out[0].value == 20.0  # (5*2)+10

    def test_predicate_limits_rule_scope(self):
        t = self._make_transformer()
        t.add_rule(
            TransformRule(
                "only-a",
                lambda r: r.metric.source == "a",
                lambda r: replace(r, value=0.0),
            )
        )
        results = [make_result(source="a", value=9.0), make_result(source="b", value=9.0)]
        out, report = t.transform(results)
        assert out[0].value == 0.0
        assert out[1].value == 9.0
        assert report.transformed == 1

    def test_rules_applied_list_is_sorted(self):
        t = self._make_transformer()
        for name in ["z-rule", "a-rule", "m-rule"]:
            t.add_rule(TransformRule(name, lambda r: True, lambda r: r))
        _, report = t.transform([make_result()])
        assert report.rules_applied == sorted(report.rules_applied)
