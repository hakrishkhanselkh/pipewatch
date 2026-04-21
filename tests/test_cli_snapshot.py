"""Tests for pipewatch.cli_snapshot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.cli_snapshot import build_parser, main


def _write_results(path: Path, results):
    from pipewatch.snapshotter import _result_to_dict
    path.write_text(json.dumps([_result_to_dict(r) for r in results]))


def make_result(source="db", name="rows", value=10.0, status=MetricStatus.OK):
    return MetricResult(
        metric=Metric(source=source, name=name),
        value=value,
        status=status,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def test_save_command_creates_snapshot(tmp_path):
    results_file = tmp_path / "results.json"
    _write_results(results_file, [make_result()])
    snap_dir = tmp_path / "snaps"
    main(["save", str(results_file), "--dir", str(snap_dir)])
    assert any(snap_dir.glob("snapshot_*.json"))


def test_save_with_label(tmp_path):
    results_file = tmp_path / "results.json"
    _write_results(results_file, [make_result()])
    snap_dir = tmp_path / "snaps"
    main(["save", str(results_file), "--dir", str(snap_dir), "--label", "nightly"])
    files = list(snap_dir.glob("snapshot_nightly_*.json"))
    assert len(files) == 1


def test_load_command_prints_results(tmp_path, capsys):
    from pipewatch.snapshotter import Snapshotter
    snap = Snapshotter(directory=str(tmp_path))
    path = snap.save([make_result(value=99.0)])
    main(["load", str(path)])
    captured = capsys.readouterr()
    assert "99" in captured.out or "rows" in captured.out


def test_list_command_shows_files(tmp_path, capsys):
    from pipewatch.snapshotter import Snapshotter
    snap = Snapshotter(directory=str(tmp_path))
    snap.save([make_result()], label="x")
    snap.save([make_result()], label="y")
    main(["list", "--dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert out.count("snapshot_") == 2


def test_list_empty_directory(tmp_path, capsys):
    main(["list", "--dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert "No snapshots found" in out


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None


def test_missing_command_exits():
    with pytest.raises(SystemExit):
        main([])
