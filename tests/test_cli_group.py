"""Integration tests for pipewatch.cli_group."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.snapshotter import Snapshotter
from pipewatch.cli_group import build_parser, main


def make_result(
    source: str = "src",
    name: str = "metric",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    metric = Metric(name=name, source=source)
    return MetricResult(metric=metric, value=value, status=status)


def _write_results(path: Path, results: list[MetricResult]) -> None:
    s = Snapshotter(path)
    s.save(results, label="test")


@pytest.fixture()
def results_file(tmp_path):
    p = tmp_path / "snap.json"
    _write_results(p, [
        make_result(source="db", name="latency", status=MetricStatus.OK),
        make_result(source="db", name="errors", status=MetricStatus.CRITICAL),
        make_result(source="api", name="latency", status=MetricStatus.WARNING),
        make_result(source="api", name="errors", status=MetricStatus.OK),
        make_result(source="cache", name="hit_rate", status=MetricStatus.OK),
    ])
    return str(p)


def test_parser_defaults():
    p = build_parser()
    args = p.parse_args(["snap.json"])
    assert args.by == "source"
    assert args.as_json is False
    assert args.min_count == 1


def test_parser_custom_by():
    p = build_parser()
    args = p.parse_args(["snap.json", "--by", "status"])
    assert args.by == "status"


def test_text_output_contains_group_keys(results_file, capsys):
    main([results_file, "--by", "source"])
    out = capsys.readouterr().out
    assert "db" in out
    assert "api" in out
    assert "cache" in out


def test_json_output_is_valid(results_file, capsys):
    main([results_file, "--by", "source", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    keys = {item["key"] for item in data}
    assert keys == {"db", "api", "cache"}


def test_json_output_fields_present(results_file, capsys):
    main([results_file, "--by", "source", "--json"])
    data = json.loads(capsys.readouterr().out)
    for item in data:
        assert "key" in item
        assert "count" in item
        assert "ok" in item
        assert "warning" in item
        assert "critical" in item
        assert "worst_status" in item


def test_group_by_status(results_file, capsys):
    main([results_file, "--by", "status", "--json"])
    data = json.loads(capsys.readouterr().out)
    statuses = {item["key"] for item in data}
    assert "ok" in statuses
    assert "critical" in statuses
    assert "warning" in statuses


def test_min_count_filters_small_groups(results_file, capsys):
    # cache has only 1 result; --min-count 2 should exclude it
    main([results_file, "--by", "source", "--json", "--min-count", "2"])
    data = json.loads(capsys.readouterr().out)
    keys = {item["key"] for item in data}
    assert "cache" not in keys
    assert "db" in keys


def test_missing_file_exits(tmp_path):
    missing = str(tmp_path / "nope.json")
    with pytest.raises(SystemExit):
        main([missing])
