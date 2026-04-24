"""Tests for pipewatch.cli_profile."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from pipewatch.cli_profile import build_parser, main


@pytest.fixture()
def profile_file(tmp_path: Path) -> Path:
    data = {
        "entries": [
            {"source": "alpha", "metric_name": "latency", "duration_seconds": 0.8},
            {"source": "beta", "metric_name": "errors", "duration_seconds": 0.2},
            {"source": "alpha", "metric_name": "throughput", "duration_seconds": 1.5},
        ]
    }
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(data))
    return p


def test_default_top_is_5():
    parser = build_parser()
    args = parser.parse_args(["some_file.json"])
    assert args.top == 5


def test_custom_top():
    parser = build_parser()
    args = parser.parse_args(["f.json", "--top", "3"])
    assert args.top == 3


def test_json_flag_default_false():
    parser = build_parser()
    args = parser.parse_args(["f.json"])
    assert args.as_json is False


def test_main_text_output(profile_file: Path, capsys):
    main([str(profile_file)])
    captured = capsys.readouterr()
    assert "Total" in captured.out
    assert "alpha" in captured.out or "beta" in captured.out


def test_main_json_output(profile_file: Path, capsys):
    main([str(profile_file), "--json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert all("source" in item for item in parsed)
    assert all("duration_seconds" in item for item in parsed)


def test_main_missing_file_exits(tmp_path: Path):
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nonexistent.json")])
    assert exc_info.value.code == 1


def test_main_top_limits_json_output(profile_file: Path, capsys):
    main([str(profile_file), "--json", "--top", "2"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert len(parsed) <= 2
