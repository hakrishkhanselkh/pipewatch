"""Integration tests for pipewatch.cli_lint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipewatch.cli_lint import main


def _write_results(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "results.json"
    p.write_text(json.dumps(rows))
    return p


@pytest.fixture()
def clean_file(tmp_path: Path) -> Path:
    return _write_results(
        tmp_path,
        [
            {
                "name": "latency",
                "value": 1.5,
                "status": "ok",
                "source": "pipe_a",
                "warning_threshold": 5.0,
                "critical_threshold": 10.0,
            }
        ],
    )


@pytest.fixture()
def dirty_file(tmp_path: Path) -> Path:
    return _write_results(
        tmp_path,
        [
            {
                "name": "latency",
                "value": None,
                "status": "ok",
                "source": "pipe_a",
                "warning_threshold": None,
                "critical_threshold": None,
            }
        ],
    )


def test_clean_file_exits_zero(clean_file: Path) -> None:
    main([str(clean_file)])


def test_dirty_file_exits_one(dirty_file: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([str(dirty_file)])
    assert exc_info.value.code == 1


def test_errors_only_suppresses_warnings(tmp_path: Path, capsys) -> None:
    p = _write_results(
        tmp_path,
        [
            {
                "name": "m",
                "value": -1.0,
                "status": "ok",
                "source": "s",
                "warning_threshold": 5.0,
                "critical_threshold": None,
            }
        ],
    )
    main([str(p), "--errors-only"])
    captured = capsys.readouterr()
    assert "WARNING" not in captured.out


def test_fail_on_warning_exits_one(tmp_path: Path) -> None:
    p = _write_results(
        tmp_path,
        [
            {
                "name": "m",
                "value": -1.0,
                "status": "ok",
                "source": "s",
                "warning_threshold": 5.0,
                "critical_threshold": None,
            }
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main([str(p), "--fail-on-warning"])
    assert exc_info.value.code == 1


def test_missing_file_exits_2(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([str(tmp_path / "nonexistent.json")])
    assert exc_info.value.code == 2
