"""Generates human-readable pipeline health reports from MetricResults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.summarizer import Summarizer, PipelineSummary


@dataclass
class ReportSection:
    title: str
    lines: List[str] = field(default_factory=list)

    def render(self) -> str:
        header = f"=== {self.title} ==="
        return "\n".join([header] + self.lines)


@dataclass
class PipelineReport:
    summary: PipelineSummary
    sections: List[ReportSection] = field(default_factory=list)
    title: str = "Pipeline Health Report"

    def render(self) -> str:
        parts = [self.title, "-" * len(self.title), str(self.summary)]
        for section in self.sections:
            parts.append("")
            parts.append(section.render())
        return "\n".join(parts)

    def __str__(self) -> str:
        return self.render()


class Reporter:
    """Builds a PipelineReport from a list of MetricResults."""

    STATUS_SYMBOLS = {
        MetricStatus.OK: "[OK]",
        MetricStatus.WARNING: "[WARN]",
        MetricStatus.CRITICAL: "[CRIT]",
    }

    def __init__(self, include_ok: bool = True) -> None:
        self.include_ok = include_ok

    def build(self, results: List[MetricResult], title: str = "Pipeline Health Report") -> PipelineReport:
        summarizer = Summarizer()
        summary = summarizer.summarize(results)

        by_source: dict[str, List[MetricResult]] = {}
        for r in results:
            by_source.setdefault(r.source, []).append(r)

        sections: List[ReportSection] = []
        for source, source_results in sorted(by_source.items()):
            section = ReportSection(title=source)
            for r in source_results:
                if not self.include_ok and r.status == MetricStatus.OK:
                    continue
                symbol = self.STATUS_SYMBOLS.get(r.status, "[?]")
                msg = f"  {symbol} {r.metric.name}: {r.value}"
                if r.message:
                    msg += f" — {r.message}"
                section.lines.append(msg)
            if section.lines:
                sections.append(section)

        return PipelineReport(summary=summary, sections=sections, title=title)
