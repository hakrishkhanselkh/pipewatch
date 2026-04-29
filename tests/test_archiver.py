"""Tests for pipewatch.archiver."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from pipewatch.archiver import Archiver, ArchiveEntry
from pipewatch.metrics import MetricResult, MetricStatus


def make_result(
    source="src",
    name="latency",
    value=1.5,
    status=MetricStatus.OK,
) -> MetricResult:
    return MetricResult(
        source=source,
        metric_name=name,
        value=value,
        status=status,
        timestamp=None,
    )


@pytest.fixture()
def archiver(tmp_path):
    return Archiver(archive_dir=tmp_path / "archives")


def test_archive_creates_file(archiver, tmp_path):
    results = [make_result()]
    entry = archiver.archive(results, label="test")
    assert entry.path.exists()
    assert entry.result_count == 1


def test_archive_entry_str_contains_label(archiver):
    entry = archiver.archive([make_result()], label="my run")
    assert "my_run" in str(entry)


def test_archive_file_is_valid_json(archiver):
    results = [make_result(value=3.0), make_result(source="db", value=0.5)]
    entry = archiver.archive(results)
    data = json.loads(entry.path.read_text())
    assert "results" in data
    assert len(data["results"]) == 2


def test_load_roundtrip(archiver):
    original = [make_result(value=7.7, status=MetricStatus.WARNING)]
    entry = archiver.archive(original, label="roundtrip")
    loaded = archiver.load(entry.path)
    assert len(loaded) == 1
    assert loaded[0].value == pytest.approx(7.7)
    assert loaded[0].status == MetricStatus.WARNING


def test_list_archives_returns_entries(archiver):
    archiver.archive([make_result()], label="a")
    archiver.archive([make_result()], label="b")
    entries = archiver.list_archives()
    assert len(entries) == 2
    labels = {e.label for e in entries}
    assert labels == {"a", "b"}


def test_purge_removes_old_entries(archiver):
    old_ts = datetime(2000, 1, 1, tzinfo=timezone.utc)
    entry = archiver.archive([make_result()], label="old", now=old_ts)
    assert entry.path.exists()

    cutoff = datetime(2001, 1, 1, tzinfo=timezone.utc)
    removed = archiver.purge_before(cutoff)
    assert removed == 1
    assert not entry.path.exists()
    assert archiver.list_archives() == []


def test_purge_keeps_recent_entries(archiver):
    recent_ts = datetime.now(timezone.utc)
    archiver.archive([make_result()], label="recent", now=recent_ts)
    cutoff = recent_ts - timedelta(days=1)
    removed = archiver.purge_before(cutoff)
    assert removed == 0
    assert len(archiver.list_archives()) == 1


def test_archive_dir_created_automatically(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    assert not deep.exists()
    Archiver(archive_dir=deep)
    assert deep.exists()
