"""Tests for pipewatch.snapshotter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.snapshotter import Snapshotter, _result_to_dict, _dict_to_result


def make_result(
    source="src",
    name="latency",
    value=1.5,
    status=MetricStatus.OK,
    ts=None,
) -> MetricResult:
    return MetricResult(
        metric=Metric(source=source, name=name),
        value=value,
        status=status,
        timestamp=ts or datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestResultSerialisation:
    def test_to_dict_fields(self):
        r = make_result()
        d = _result_to_dict(r)
        assert d["source"] == "src"
        assert d["name"] == "latency"
        assert d["value"] == 1.5
        assert d["status"] == "ok"
        assert d["timestamp"] == "20240601T120000Z"

    def test_roundtrip(self):
        original = make_result(value=42.0, status=MetricStatus.WARNING)
        restored = _dict_to_result(_result_to_dict(original))
        assert restored.metric.source == original.metric.source
        assert restored.metric.name == original.metric.name
        assert restored.value == original.value
        assert restored.status == original.status
        assert restored.timestamp == original.timestamp

    def test_none_timestamp_roundtrip(self):
        r = MetricResult(
            metric=Metric(source="s", name="n"),
            value=0.0,
            status=MetricStatus.OK,
            timestamp=None,
        )
        restored = _dict_to_result(_result_to_dict(r))
        assert restored.timestamp is None


class TestSnapshotter:
    def test_save_creates_file(self, tmp_path):
        snap = Snapshotter(directory=str(tmp_path))
        results = [make_result()]
        path = snap.save(results)
        assert path.exists()
        assert path.suffix == ".json"

    def test_save_with_label(self, tmp_path):
        snap = Snapshotter(directory=str(tmp_path))
        path = snap.save([make_result()], label="prod")
        assert "prod" in path.name

    def test_load_returns_results(self, tmp_path):
        snap = Snapshotter(directory=str(tmp_path))
        original = [make_result(value=7.0, status=MetricStatus.CRITICAL)]
        path = snap.save(original)
        loaded = snap.load(str(path))
        assert len(loaded) == 1
        assert loaded[0].value == 7.0
        assert loaded[0].status == MetricStatus.CRITICAL

    def test_list_snapshots_sorted(self, tmp_path):
        snap = Snapshotter(directory=str(tmp_path))
        r = make_result()
        p1 = snap.save([r], label="a")
        p2 = snap.save([r], label="b")
        listed = snap.list_snapshots()
        assert listed[0] <= listed[-1]  # sorted oldest first
        assert len(listed) == 2

    def test_list_empty_directory(self, tmp_path):
        snap = Snapshotter(directory=str(tmp_path))
        assert snap.list_snapshots() == []

    def test_save_multiple_results(self, tmp_path):
        snap = Snapshotter(directory=str(tmp_path))
        results = [make_result(name=f"m{i}", value=float(i)) for i in range(5)]
        path = snap.save(results)
        loaded = snap.load(str(path))
        assert len(loaded) == 5
