"""Tests for pipewatch.cli_archive."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipewatch.cli_archive import main, build_parser
from pipewatch.metrics import MetricStatus
from pipewatch.snapshotter import _result_to_dict
from pipewatch.metrics import MetricResult


def make_result(
    source="pipe",
    name="rows",
    value=10.0,
    status=MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        source=source,
        metric_name=name,
        value=value,
        status=status,
        timestamp=None,
    )


def _write_results(path: Path, results) -> None:
    path.write_text(json.dumps([_result_to_dict(r) for r in results]))


@pytest.fixture()
def results_file(tmp_path):
    p = tmp_path / "results.json"
    _write_results(p, [make_result(), make_result(source="db", value=5.0)])
    return p


def test_save_command_creates_archive(results_file, tmp_path, capsys):
    archive_dir = tmp_path / "arc"
    main(["--archive-dir", str(archive_dir), "save", str(results_file)])
    out = capsys.readouterr().out
    assert "Archived 2 result(s)" in out
    files = list(archive_dir.glob("*.json"))
    assert len(files) == 1


def test_save_with_custom_label(results_file, tmp_path, capsys):
    archive_dir = tmp_path / "arc"
    main(["--archive-dir", str(archive_dir), "save", str(results_file), "--label", "nightly"])
    files = list(archive_dir.glob("*nightly*.json"))
    assert len(files) == 1


def test_load_command_prints_results(results_file, tmp_path, capsys):
    archive_dir = tmp_path / "arc"
    main(["--archive-dir", str(archive_dir), "save", str(results_file)])
    arc_file = next((archive_dir).glob("*.json"))
    main(["--archive-dir", str(archive_dir), "load", str(arc_file)])
    out = capsys.readouterr().out
    assert "pipe/rows" in out
    assert "db/rows" in out


def test_purge_command_reports_count(results_file, tmp_path, capsys):
    archive_dir = tmp_path / "arc"
    main(["--archive-dir", str(archive_dir), "save", str(results_file)])
    # Purge with 0 days — nothing should be older than now
    main(["--archive-dir", str(archive_dir), "purge", "--days", "0"])
    out = capsys.readouterr().out
    assert "Purged" in out


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["save", "some_file.json"])
    assert args.archive_dir == ".pipewatch_archives"
    assert args.label == "archive"
