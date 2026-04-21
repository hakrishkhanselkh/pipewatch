"""CLI entry point for generating pipeline health reports."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.reporter import Reporter


def _load_results(path: str) -> List[MetricResult]:
    from pipewatch.cli_export import _parse_result  # reuse if available
    try:
        from pipewatch.cli_aggregate import _parse_result as parse_fn
    except ImportError:
        parse_fn = None

    with open(path) as fh:
        data = json.load(fh)

    results = []
    for item in data:
        from pipewatch.metrics import Metric
        metric = Metric(name=item["name"], source=item["source"])
        status = MetricStatus[item["status"].upper()]
        results.append(
            MetricResult(
                metric=metric,
                value=item.get("value", 0.0),
                status=status,
                message=item.get("message"),
                source=item["source"],
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-report",
        description="Generate a human-readable pipeline health report.",
    )
    parser.add_argument("input", help="Path to JSON results file")
    parser.add_argument(
        "--title", default="Pipeline Health Report", help="Report title"
    )
    parser.add_argument(
        "--hide-ok", action="store_true", help="Omit OK results from the report"
    )
    parser.add_argument(
        "--output", "-o", default=None, help="Write report to file instead of stdout"
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = _load_results(args.input)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error loading results: {exc}", file=sys.stderr)
        sys.exit(1)

    reporter = Reporter(include_ok=not args.hide_ok)
    report = reporter.build(results, title=args.title)
    rendered = report.render()

    if args.output:
        with open(args.output, "w") as fh:
            fh.write(rendered + "\n")
        print(f"Report written to {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
