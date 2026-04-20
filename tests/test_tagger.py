"""Tests for pipewatch.tagger."""

from __future__ import annotations

import pytest

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.tagger import ResultTagger, TagIndex


def make_result(
    source: str = "src",
    name: str = "metric",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
    message: str = "",
) -> MetricResult:
    return MetricResult(source=source, name=name, value=value, status=status, message=message)


# --- TagIndex ---

class TestTagIndex:
    def test_add_and_get(self):
        idx = TagIndex()
        r = make_result()
        idx.add(r, ["alpha", "beta"])
        assert r in idx.get("alpha")
        assert r in idx.get("beta")

    def test_get_unknown_tag_returns_empty(self):
        idx = TagIndex()
        assert idx.get("nope") == []

    def test_all_tags(self):
        idx = TagIndex()
        idx.add(make_result(), ["x", "y"])
        assert idx.all_tags() == {"x", "y"}

    def test_len_counts_all_entries(self):
        idx = TagIndex()
        r1, r2 = make_result(), make_result(name="b")
        idx.add(r1, ["a"])
        idx.add(r2, ["a", "b"])
        assert len(idx) == 3  # r1->a, r2->a, r2->b


# --- ResultTagger ---

class TestResultTagger:
    def test_tag_and_retrieve(self):
        tagger = ResultTagger()
        r = make_result()
        tagger.tag(r, "prod", "critical")
        assert "prod" in tagger.tags_for(r)
        assert "critical" in tagger.tags_for(r)

    def test_tags_for_untagged_result(self):
        tagger = ResultTagger()
        r = make_result()
        assert tagger.tags_for(r) == set()

    def test_by_tag_returns_correct_results(self):
        tagger = ResultTagger()
        r1 = make_result(name="m1")
        r2 = make_result(name="m2")
        tagger.tag(r1, "env:prod")
        tagger.tag(r2, "env:staging")
        assert tagger.by_tag("env:prod") == [r1]
        assert tagger.by_tag("env:staging") == [r2]

    def test_by_all_tags_intersection(self):
        tagger = ResultTagger()
        r1 = make_result(name="m1")
        r2 = make_result(name="m2")
        tagger.tag(r1, "a", "b")
        tagger.tag(r2, "a")
        result = tagger.by_all_tags("a", "b")
        assert r1 in result
        assert r2 not in result

    def test_by_all_tags_empty_input(self):
        tagger = ResultTagger()
        tagger.tag(make_result(), "a")
        assert tagger.by_all_tags() == []

    def test_duplicate_tags_ignored(self):
        tagger = ResultTagger()
        r = make_result()
        tagger.tag(r, "x")
        tagger.tag(r, "x")
        assert tagger.by_tag("x") == [r]  # only one entry

    def test_all_tags_aggregated(self):
        tagger = ResultTagger()
        tagger.tag(make_result(name="a"), "t1")
        tagger.tag(make_result(name="b"), "t2")
        assert tagger.all_tags() == {"t1", "t2"}
