"""CLI command for exporting pipeline metric results."""

from __future__ import annotations

import argparse
import sys
from typing import List

from pipewatch.exporters import CsvExporter, JsonExporter, MarkdownExporter
from pipewatch.metrics import MetricResult

_EXPORTERS = {
    "json": JsonExporter,
    "csv": CsvExporter,
    "markdown": MarkdownExporter,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch export",
        description="Export collected metric results to a chosen format.",
    )
    parser.add_argument(
        "--format",
        choices=list(_EXPORTERS.keys()),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    return parser


def export_results(
    results: List[MetricResult],
    fmt: str = "json",
    output_path: str | None = None,
) -> None:
    """Serialize *results* in *fmt* and write to *output_path* or stdout."""
    exporter_cls = _EXPORTERS.get(fmt)
    if exporter_cls is None:
        raise ValueError(f"Unknown export format: {fmt!r}")

    exporter = exporter_cls()
    content = exporter.export(results)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(content)
    else:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")


def main(argv: List[str] | None = None) -> None:
    """Entry point — intended for use with a runner that supplies results."""
    parser = build_parser()
    args = parser.parse_args(argv)
    # When invoked standalone there are no results; print usage hint.
    parser.print_help()
    sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
