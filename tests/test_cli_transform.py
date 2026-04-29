"""Tests for pipewatch.cli_transform."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.snapshotter import _result_to_dict
from pipewatch.cli_transform import build_parser, main


def make_result(
    source: str = "db",
    name: str = "latency",
    value: float = 1.0,
    status: MetricStatus = MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        metric=Metric(source=source, name=name),
        value=value,
        status=status,
    )


def _write_results(path: Path, results) -> None:
    path.write_text(json.dumps([_result_to_dict(r) for r in results]))


@pytest.fixture
def results_file(tmp_path):
    p = tmp_path / "results.json"
    _write_results(
        p,
        [
            make_result(value=-3.0),
            make_result(value=50.0),
            make_result(source="other", value=-1.0),
        ],
    )
    return p


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["results.json"])
    assert args.clamp_negative is False
    assert args.cap_value is None
    assert args.source is None
    assert args.as_json is False


def test_parser_clamp_flag():
    parser = build_parser()
    args = parser.parse_args(["results.json", "--clamp-negative"])
    assert args.clamp_negative is True


def test_parser_cap_value():
    parser = build_parser()
    args = parser.parse_args(["results.json", "--cap-value", "100"])
    assert args.cap_value == 100.0


def test_clamp_negative_text_output(results_file, capsys):
    main([str(results_file), "--clamp-negative"])
    out = capsys.readouterr().out
    assert "transformed=2" in out


def test_clamp_negative_json_output(results_file, capsys):
    main([str(results_file), "--clamp-negative", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    values = [d["value"] for d in data]
    assert all(v >= 0 for v in values)


def test_cap_value_json_output(results_file, capsys):
    main([str(results_file), "--cap-value", "10", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    values = [d["value"] for d in data]
    assert all(v <= 10 for v in values)


def test_source_filter_limits_scope(results_file, capsys):
    main([str(results_file), "--clamp-negative", "--source", "db", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    other = [d for d in data if d["source"] == "other"]
    assert other[0]["value"] == -1.0  # untouched


def test_missing_file_exits_nonzero(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path / "no_such.json")])
    assert exc.value.code != 0
