"""Tests for pipewatch.exporters."""

import csv
import io
import json

import pytest

from pipewatch.exporters import CsvExporter, JsonExporter, MarkdownExporter
from pipewatch.metrics import Metric, MetricResult, MetricStatus


def make_result(source: str, name: str, value: float, status: MetricStatus) -> MetricResult:
    metric = Metric(source=source, name=name)
    return MetricResult(metric=metric, value=value, status=status)


RESULTS = [
    make_result("db", "row_count", 1200.0, MetricStatus.OK),
    make_result("api", "latency_ms", 850.0, MetricStatus.WARNING),
    make_result("etl", "error_rate", 0.15, MetricStatus.CRITICAL),
]


class TestJsonExporter:
    def test_returns_valid_json(self):
        exporter = JsonExporter()
        output = exporter.export(RESULTS)
        data = json.loads(output)
        assert len(data) == 3

    def test_fields_present(self):
        exporter = JsonExporter()
        data = json.loads(exporter.export(RESULTS))
        for record in data:
            assert set(record.keys()) == {"source", "name", "value", "status", "timestamp"}

    def test_status_values(self):
        exporter = JsonExporter()
        data = json.loads(exporter.export(RESULTS))
        statuses = [r["status"] for r in data]
        assert statuses == ["ok", "warning", "critical"]

    def test_empty_results(self):
        exporter = JsonExporter()
        assert json.loads(exporter.export([])) == []


class TestCsvExporter:
    def test_returns_csv_with_header(self):
        exporter = CsvExporter()
        output = exporter.export(RESULTS)
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        assert len(rows) == 3

    def test_csv_columns(self):
        exporter = CsvExporter()
        output = exporter.export(RESULTS)
        reader = csv.DictReader(io.StringIO(output))
        assert reader.fieldnames == ["source", "name", "value", "status", "timestamp"]

    def test_csv_values(self):
        exporter = CsvExporter()
        output = exporter.export(RESULTS)
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        assert rows[0]["source"] == "db"
        assert rows[1]["status"] == "warning"


class TestMarkdownExporter:
    def test_contains_header_row(self):
        exporter = MarkdownExporter()
        output = exporter.export(RESULTS)
        assert "| Source | Metric | Value | Status |" in output

    def test_contains_separator(self):
        exporter = MarkdownExporter()
        output = exporter.export(RESULTS)
        assert "|--------|" in output

    def test_emoji_for_statuses(self):
        exporter = MarkdownExporter()
        output = exporter.export(RESULTS)
        assert "✅" in output
        assert "⚠️" in output
        assert "🔴" in output

    def test_row_count(self):
        exporter = MarkdownExporter()
        lines = exporter.export(RESULTS).splitlines()
        # header + separator + 3 data rows
        assert len(lines) == 5
