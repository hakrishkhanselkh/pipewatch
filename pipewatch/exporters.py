"""Exporters for serializing pipeline metric results to various formats."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import List

from pipewatch.metrics import MetricResult


def _result_to_dict(result: MetricResult) -> dict:
    return {
        "source": result.metric.source,
        "name": result.metric.name,
        "value": result.value,
        "status": result.status.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class JsonExporter:
    """Export metric results as a JSON string."""

    def __init__(self, indent: int = 2) -> None:
        self.indent = indent

    def export(self, results: List[MetricResult]) -> str:
        payload = [_result_to_dict(r) for r in results]
        return json.dumps(payload, indent=self.indent)


class CsvExporter:
    """Export metric results as a CSV string."""

    FIELDS = ["source", "name", "value", "status", "timestamp"]

    def export(self, results: List[MetricResult]) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(_result_to_dict(result))
        return buf.getvalue()


class MarkdownExporter:
    """Export metric results as a Markdown table."""

    _STATUS_EMOJI = {"ok": "✅", "warning": "⚠️", "critical": "🔴"}

    def export(self, results: List[MetricResult]) -> str:
        lines = [
            "| Source | Metric | Value | Status |",
            "|--------|--------|-------|--------|",
        ]
        for r in results:
            emoji = self._STATUS_EMOJI.get(r.status.value, "")
            lines.append(
                f"| {r.metric.source} | {r.metric.name} "
                f"| {r.value} | {emoji} {r.status.value} |"
            )
        return "\n".join(lines)
