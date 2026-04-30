"""Tests for pipewatch.partitioner."""
from __future__ import annotations

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.partitioner import Partition, PartitionReport, ResultPartitioner


def make_result(
    name: str = "latency",
    source: str = "db",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        metric=Metric(name=name, source=source),
        value=value,
        status=status,
    )


# ---------------------------------------------------------------------------
# Partition dataclass
# ---------------------------------------------------------------------------

def test_partition_len_reflects_results():
    p = Partition(name="ok")
    assert len(p) == 0
    p.results.append(make_result())
    assert len(p) == 1


def test_partition_str_contains_name_and_count():
    p = Partition(name="critical", results=[make_result()])
    s = str(p)
    assert "critical" in s
    assert "1" in s


# ---------------------------------------------------------------------------
# PartitionReport
# ---------------------------------------------------------------------------

def test_report_get_returns_partition():
    p = Partition(name="ok")
    report = PartitionReport(partitions={"ok": p})
    assert report.get("ok") is p


def test_report_get_missing_returns_none():
    report = PartitionReport()
    assert report.get("missing") is None


def test_report_partition_names():
    report = PartitionReport(
        partitions={"a": Partition("a"), "b": Partition("b")}
    )
    assert set(report.partition_names()) == {"a", "b"}


def test_report_str_contains_counts():
    report = PartitionReport(
        partitions={"ok": Partition("ok", results=[make_result()])},
        unmatched=[make_result()],
    )
    s = str(report)
    assert "ok=1" in s
    assert "unmatched=1" in s


# ---------------------------------------------------------------------------
# ResultPartitioner
# ---------------------------------------------------------------------------

def test_empty_results_produce_empty_partitions():
    rp = ResultPartitioner()
    rp.add_rule("ok", lambda r: r.status == MetricStatus.OK)
    report = rp.partition([])
    assert len(report.partitions["ok"]) == 0
    assert report.unmatched == []


def test_results_routed_to_correct_bucket():
    rp = ResultPartitioner()
    rp.add_rule("critical", lambda r: r.status == MetricStatus.CRITICAL)
    rp.add_rule("ok", lambda r: r.status == MetricStatus.OK)

    results = [
        make_result(status=MetricStatus.CRITICAL),
        make_result(status=MetricStatus.OK),
        make_result(status=MetricStatus.OK),
    ]
    report = rp.partition(results)
    assert len(report.partitions["critical"]) == 1
    assert len(report.partitions["ok"]) == 2
    assert report.unmatched == []


def test_unmatched_collected_without_default_bucket():
    rp = ResultPartitioner()
    rp.add_rule("critical", lambda r: r.status == MetricStatus.CRITICAL)

    results = [
        make_result(status=MetricStatus.OK),
        make_result(status=MetricStatus.WARNING),
    ]
    report = rp.partition(results)
    assert len(report.unmatched) == 2


def test_default_bucket_catches_unmatched():
    rp = ResultPartitioner(default_bucket="other")
    rp.add_rule("critical", lambda r: r.status == MetricStatus.CRITICAL)

    results = [
        make_result(status=MetricStatus.CRITICAL),
        make_result(status=MetricStatus.OK),
    ]
    report = rp.partition(results)
    assert len(report.partitions["critical"]) == 1
    assert len(report.partitions["other"]) == 1
    assert report.unmatched == []


def test_first_matching_rule_wins():
    rp = ResultPartitioner()
    rp.add_rule("first", lambda r: True)
    rp.add_rule("second", lambda r: True)

    report = rp.partition([make_result()])
    assert len(report.partitions["first"]) == 1
    assert len(report.partitions["second"]) == 0


def test_partition_by_source():
    rp = ResultPartitioner(default_bucket="other")
    rp.add_rule("db", lambda r: r.metric.source == "db")
    rp.add_rule("api", lambda r: r.metric.source == "api")

    results = [
        make_result(source="db"),
        make_result(source="api"),
        make_result(source="cache"),
    ]
    report = rp.partition(results)
    assert len(report.partitions["db"]) == 1
    assert len(report.partitions["api"]) == 1
    assert len(report.partitions["other"]) == 1
