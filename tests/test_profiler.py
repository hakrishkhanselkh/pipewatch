"""Tests for pipewatch.profiler."""

from __future__ import annotations

import pytest
from pipewatch.profiler import Profiler, ProfileEntry, ProfileReport


def make_profiler_with_entries() -> Profiler:
    p = Profiler()
    p.record("sourceA", "latency", 0.5)
    p.record("sourceA", "throughput", 0.1)
    p.record("sourceB", "error_rate", 1.2)
    p.record("sourceB", "queue_depth", 0.3)
    return p


class TestProfiler:
    def test_record_increases_len(self):
        p = Profiler()
        assert len(p) == 0
        p.record("src", "metric", 0.42)
        assert len(p) == 1

    def test_entries_returns_copy(self):
        p = Profiler()
        p.record("src", "m", 0.1)
        entries = p.entries()
        entries.clear()
        assert len(p) == 1

    def test_clear_resets_entries(self):
        p = make_profiler_with_entries()
        assert len(p) == 4
        p.clear()
        assert len(p) == 0

    def test_report_returns_profile_report(self):
        p = make_profiler_with_entries()
        report = p.report()
        assert isinstance(report, ProfileReport)
        assert len(report.entries) == 4


class TestProfileReport:
    def test_slowest_returns_sorted_desc(self):
        p = make_profiler_with_entries()
        report = p.report()
        slowest = report.slowest(2)
        assert len(slowest) == 2
        assert slowest[0].duration_seconds >= slowest[1].duration_seconds

    def test_slowest_clamps_to_available(self):
        p = Profiler()
        p.record("s", "m", 0.1)
        report = p.report()
        assert len(report.slowest(100)) == 1

    def test_average_duration_none_when_empty(self):
        report = ProfileReport(entries=[])
        assert report.average_duration() is None

    def test_average_duration_correct(self):
        p = make_profiler_with_entries()
        report = p.report()
        expected = (0.5 + 0.1 + 1.2 + 0.3) / 4
        assert abs(report.average_duration() - expected) < 1e-9

    def test_total_duration(self):
        p = make_profiler_with_entries()
        report = p.report()
        assert abs(report.total_duration() - 2.1) < 1e-9

    def test_str_contains_total(self):
        p = make_profiler_with_entries()
        report = p.report()
        assert "Total" in str(report)


class TestProfileEntryStr:
    def test_str_format(self):
        entry = ProfileEntry(source="db", metric_name="lag", duration_seconds=0.123)
        s = str(entry)
        assert "db/lag" in s
        assert "0.1230" in s
