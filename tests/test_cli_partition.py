"""Tests for pipewatch.cli_partition."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.cli_partition import build_parser, main
from pipewatch.snapshotter import _result_to_dict


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


def _write_results(path: Path, results: list[MetricResult]) -> None:
    path.write_text(json.dumps([_result_to_dict(r) for r in results]))


@pytest.fixture()
def results_file(tmp_path):
    f = tmp_path / "results.json"
    _write_results(
        f,
        [
            make_result(source="db", status=MetricStatus.OK),
            make_result(source="api", status=MetricStatus.CRITICAL),
            make_result(source="db", status=MetricStatus.WARNING),
        ],
    )
    return str(f)


def test_parser_defaults():
    p = build_parser()
    args = p.parse_args(["results.json"])
    assert args.by == "status"
    assert args.default_bucket == "other"
    assert args.json is False


def test_parser_custom_by():
    p = build_parser()
    args = p.parse_args(["results.json", "--by", "source"])
    assert args.by == "source"


def test_text_output_by_status(results_file, capsys):
    main([results_file, "--by", "status"])
    out = capsys.readouterr().out
    assert "critical" in out
    assert "warning" in out
    assert "ok" in out


def test_json_output_by_status(results_file, capsys):
    main([results_file, "--by", "status", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "critical" in data
    assert "ok" in data
    assert data["critical"] == 1
    assert data["ok"] == 1


def test_json_output_by_source(results_file, capsys):
    main([results_file, "--by", "source", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "db" in data
    assert "api" in data
    assert data["db"] == 2
    assert data["api"] == 1


def test_missing_file_exits_one(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nope.json")])
    assert exc_info.value.code == 1
