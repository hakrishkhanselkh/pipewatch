"""CLI entry point: pipewatch-lint — lint a JSON results file for issues."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipewatch.linter import PipelineLinter
from pipewatch.metrics import Metric, MetricResult, MetricStatus


def _load_results(path: str) -> list[MetricResult]:
    data = json.loads(Path(path).read_text())
    results: list[MetricResult] = []
    for item in data:
        metric = Metric(
            name=item["name"],
            warning_threshold=item.get("warning_threshold"),
            critical_threshold=item.get("critical_threshold"),
        )
        results.append(
            MetricResult(
                metric=metric,
                value=item.get("value"),
                status=MetricStatus(item["status"]),
                source=item.get("source", ""),
                timestamp=item.get("timestamp"),
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-lint",
        description="Lint a pipewatch results JSON file for configuration and data issues.",
    )
    parser.add_argument("file", help="Path to the JSON results file")
    parser.add_argument(
        "--errors-only",
        action="store_true",
        default=False,
        help="Only print errors, suppress warnings",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        default=False,
        help="Exit with code 1 if any warnings are present",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = _load_results(args.file)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        print(f"Error loading results: {exc}", file=sys.stderr)
        sys.exit(2)

    linter = PipelineLinter()
    report = linter.lint(results)

    issues = report.errors if args.errors_only else report.issues
    for issue in issues:
        print(issue)

    if not issues:
        print("Lint passed: no issues found.")

    if not report.is_clean:
        sys.exit(1)
    if args.fail_on_warning and report.warnings:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
