"""Tests for pipewatch.cli_report."""

from __future__ import annotations

import json
import os
import sys
import pytest

from pipewatch.cli_report import build_parser, main


SAMPLE_DATA = [
    {"name": "row_count", "source": "db", "status": "ok", "value": 500.0, "message": None},
    {"name": "latency", "source": "db", "status": "warning", "value": 320.0, "message": "High latency"},
    {"name": "error_rate", "source": "api", "status": "critical", "value": 0.15, "message": "Too many errors"},
]


@pytest.fixture
def results_file(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(SAMPLE_DATA))
    return str(path)


def test_default_title_in_output(results_file, capsys):
    main([results_file])
    captured = capsys.readouterr()
    assert "Pipeline Health Report" in captured.out


def test_custom_title(results_file, capsys):
    main([results_file, "--title", "Nightly Check"])
    captured = capsys.readouterr()
    assert "Nightly Check" in captured.out


def test_hide_ok_flag(results_file, capsys):
    main([results_file, "--hide-ok"])
    captured = capsys.readouterr()
    assert "row_count" not in captured.out
    assert "latency" in captured.out


def test_output_to_file(results_file, tmp_path):
    out_path = str(tmp_path / "report.txt")
    main([results_file, "--output", out_path])
    assert os.path.exists(out_path)
    content = open(out_path).read()
    assert "Pipeline Health Report" in content


def test_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nonexistent.json")])
    assert exc_info.value.code != 0


def test_invalid_json_exits(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(SystemExit) as exc_info:
        main([str(bad)])
    assert exc_info.value.code != 0


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None
    args = parser.parse_args(["somefile.json"])
    assert args.input == "somefile.json"
    assert args.hide_ok is False
    assert args.output is None
