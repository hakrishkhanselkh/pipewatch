"""Tests for pipewatch.scorer."""

from __future__ import annotations

import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.scorer import ResultScorer, ScoreReport


def make_result(
    status: MetricStatus,
    source: str = "src",
    name: str = "metric",
    value: float = 1.0,
) -> MetricResult:
    return MetricResult(source=source, name=name, value=value, status=status)


# ---------------------------------------------------------------------------
# ScoreReport grade assignment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "score, expected_grade",
    [
        (100.0, "A"),
        (90.0, "A"),
        (89.9, "B"),
        (75.0, "B"),
        (74.9, "C"),
        (50.0, "C"),
        (49.9, "D"),
        (25.0, "D"),
        (24.9, "F"),
        (0.0, "F"),
    ],
)
def test_grade_boundaries(score: float, expected_grade: str) -> None:
    report = ScoreReport(
        score=score, total=10, ok_count=5, warning_count=3, critical_count=2
    )
    assert report.grade == expected_grade


def test_score_report_str_contains_grade() -> None:
    report = ScoreReport(
        score=80.0, total=4, ok_count=3, warning_count=1, critical_count=0
    )
    assert "Grade B" in str(report)
    assert "80.0" in str(report)


# ---------------------------------------------------------------------------
# ResultScorer.score
# ---------------------------------------------------------------------------


def test_empty_results_returns_100() -> None:
    scorer = ResultScorer()
    report = scorer.score([])
    assert report.score == 100.0
    assert report.total == 0
    assert report.grade == "A"


def test_all_ok_returns_100() -> None:
    scorer = ResultScorer()
    results = [make_result(MetricStatus.OK) for _ in range(5)]
    report = scorer.score(results)
    assert report.score == 100.0
    assert report.ok_count == 5


def test_all_critical_returns_0() -> None:
    scorer = ResultScorer()
    results = [make_result(MetricStatus.CRITICAL) for _ in range(4)]
    report = scorer.score(results)
    assert report.score == 0.0
    assert report.critical_count == 4


def test_mixed_results_score_is_between_0_and_100() -> None:
    scorer = ResultScorer()
    results = [
        make_result(MetricStatus.OK),
        make_result(MetricStatus.WARNING),
        make_result(MetricStatus.CRITICAL),
        make_result(MetricStatus.OK),
    ]
    report = scorer.score(results)
    assert 0.0 < report.score < 100.0
    assert report.total == 4
    assert report.ok_count == 2
    assert report.warning_count == 1
    assert report.critical_count == 1


def test_custom_weights_affect_score() -> None:
    """Higher warning weight should produce a lower score for same results."""
    results = [
        make_result(MetricStatus.OK),
        make_result(MetricStatus.WARNING),
    ]
    scorer_low = ResultScorer(warning_weight=0.1)
    scorer_high = ResultScorer(warning_weight=0.9)
    assert scorer_low.score(results).score > scorer_high.score(results).score


def test_counts_are_accurate() -> None:
    scorer = ResultScorer()
    results = [
        make_result(MetricStatus.OK),
        make_result(MetricStatus.OK),
        make_result(MetricStatus.WARNING),
        make_result(MetricStatus.CRITICAL),
        make_result(MetricStatus.CRITICAL),
    ]
    report = scorer.score(results)
    assert report.ok_count == 2
    assert report.warning_count == 1
    assert report.critical_count == 2
    assert report.total == 5
