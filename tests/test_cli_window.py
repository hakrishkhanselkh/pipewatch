"""Tests for pipewatch.cli_window."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from pipewatch.cli_window import build_parser, main


def make_result(
    source: str = "db",
    name: str = "query_time",
    value: float = 1.0,
    status: str = "ok",
    ts: str | None = None,
) -> dict:
    return {
        "source": source,
        "name": name,
        "value": value,
        "status": status,
        "timestamp": ts or datetime.utcnow().isoformat(),
    }


def _write_results(path: Path, items: list) -> None:
    path.write_text(json.dumps(items))


@pytest.fixture()
def results_file(tmp_path: Path) -> Path:
    p = tmp_path / "results.json"
    _write_results(p, [
        make_result(value=2.0, status="ok"),
        make_result(value=5.0, status="warning"),
        make_result(source="cache", name="hits", value=0.5, status="critical"),
    ])
    return p


def test_parser_defaults():
    p = build_parser()
    args = p.parse_args(["results.json"])
    assert args.window == 60.0
    assert args.source is None
    assert args.json is False


def test_parser_custom_window():
    p = build_parser()
    args = p.parse_args(["results.json", "--window", "120"])
    assert args.window == 120.0


def test_main_text_output(results_file: Path, capsys):
    main([str(results_file)])
    out = capsys.readouterr().out
    assert "db/query_time" in out or "cache/hits" in out


def test_main_json_output(results_file: Path, capsys):
    main([str(results_file), "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "avg" in data[0]


def test_source_filter(results_file: Path, capsys):
    main([str(results_file), "--source", "cache"])
    out = capsys.readouterr().out
    assert "cache" in out
    assert "db" not in out


def test_missing_file_exits_nonzero(tmp_path: Path):
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "no_such.json")])
    assert exc_info.value.code != 0


def test_invalid_window_exits_nonzero(results_file: Path):
    with pytest.raises(SystemExit) as exc_info:
        main([str(results_file), "--window", "-5"])
    assert exc_info.value.code != 0
