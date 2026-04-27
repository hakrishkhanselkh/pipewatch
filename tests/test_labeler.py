"""Tests for pipewatch.labeler."""

from datetime import datetime

import pytest

from pipewatch.labeler import Labeler, LabeledResult
from pipewatch.metrics import Metric, MetricResult, MetricStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_result(
    name: str = "row_count",
    source: str = "db",
    value: float = 100.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    metric = Metric(name=name, source=source)
    return MetricResult(
        metric=metric,
        value=value,
        status=status,
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture()
def labeler() -> Labeler:
    return Labeler()


# ---------------------------------------------------------------------------
# LabeledResult
# ---------------------------------------------------------------------------

def test_labeled_result_get_existing_key():
    r = make_result()
    lr = LabeledResult(result=r, labels={"env": "prod"})
    assert lr.get("env") == "prod"


def test_labeled_result_get_missing_key():
    r = make_result()
    lr = LabeledResult(result=r)
    assert lr.get("env") is None


# ---------------------------------------------------------------------------
# Labeler.label
# ---------------------------------------------------------------------------

def test_label_returns_labeled_result(labeler):
    r = make_result()
    lr = labeler.label(r, env="prod")
    assert isinstance(lr, LabeledResult)
    assert lr.result is r
    assert lr.get("env") == "prod"


def test_label_merges_with_existing(labeler):
    r = make_result()
    labeler.label(r, env="prod")
    lr = labeler.label(r, team="data")
    assert lr.get("env") == "prod"
    assert lr.get("team") == "data"


def test_label_overwrites_same_key(labeler):
    r = make_result()
    labeler.label(r, env="prod")
    lr = labeler.label(r, env="staging")
    assert lr.get("env") == "staging"


def test_len_tracks_unique_results(labeler):
    r1, r2 = make_result(name="a"), make_result(name="b")
    labeler.label(r1, env="prod")
    labeler.label(r1, team="data")  # same result, no new entry
    labeler.label(r2, env="dev")
    assert len(labeler) == 2


# ---------------------------------------------------------------------------
# Labeler.label_many
# ---------------------------------------------------------------------------

def test_label_many_applies_to_all(labeler):
    results = [make_result(name=n) for n in ("a", "b", "c")]
    labeled = labeler.label_many(results, env="prod")
    assert len(labeled) == 3
    assert all(lr.get("env") == "prod" for lr in labeled)


# ---------------------------------------------------------------------------
# Labeler.get
# ---------------------------------------------------------------------------

def test_get_returns_none_for_unknown(labeler):
    r = make_result()
    assert labeler.get(r) is None


def test_get_returns_labeled_result_after_label(labeler):
    r = make_result()
    labeler.label(r, env="prod")
    lr = labeler.get(r)
    assert lr is not None
    assert lr.get("env") == "prod"


# ---------------------------------------------------------------------------
# Labeler.find_by_label
# ---------------------------------------------------------------------------

def test_find_by_label_returns_matching(labeler):
    r1 = make_result(name="a")
    r2 = make_result(name="b")
    r3 = make_result(name="c")
    labeler.label(r1, env="prod")
    labeler.label(r2, env="prod")
    labeler.label(r3, env="dev")
    found = labeler.find_by_label("env", "prod")
    assert len(found) == 2
    assert all(lr.get("env") == "prod" for lr in found)


def test_find_by_label_empty_when_no_match(labeler):
    r = make_result()
    labeler.label(r, env="prod")
    assert labeler.find_by_label("env", "staging") == []


# ---------------------------------------------------------------------------
# Labeler.all_labeled
# ---------------------------------------------------------------------------

def test_all_labeled_returns_all(labeler):
    r1, r2 = make_result(name="x"), make_result(name="y")
    labeler.label(r1, env="prod")
    labeler.label(r2, env="dev")
    assert len(labeler.all_labeled()) == 2


def test_all_labeled_empty_initially(labeler):
    assert labeler.all_labeled() == []
