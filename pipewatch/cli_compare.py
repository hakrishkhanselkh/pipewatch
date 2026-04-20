"""CLI entry point for comparing two exported result snapshots."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.comparator import ResultComparator
from pipewatch.metrics import MetricResult, MetricStatus


def _load_results(path: str) -> List[MetricResult]:
    data = json.loads(Path(path).read_text())
    results = []
    for item in data:
        try:
            results.append(
                MetricResult(
                    source=item["source"],
                    name=item["name"],
                    value=float(item["value"]),
                    status=MetricStatus(item["status"]),
                    message=item.get("message"),
                )
            )
        except (KeyError, ValueError) as exc:
            print(f"Warning: skipping malformed record — {exc}", file=sys.stderr)
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-compare",
        description="Compare two result snapshots and report status changes.",
    )
    parser.add_argument(
        "previous",
        metavar="PREVIOUS",
        help="Path to the previous JSON snapshot.",
    )
    parser.add_argument(
        "current",
        metavar="CURRENT",
        help="Path to the current JSON snapshot.",
    )
    parser.add_argument(
        "--degraded-only",
        action="store_true",
        default=False,
        help="Exit with code 1 if any metrics have degraded.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress output; only use exit codes.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        previous = _load_results(args.previous)
        current = _load_results(args.current)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error loading snapshots: {exc}", file=sys.stderr)
        return 2

    report = ResultComparator().compare(previous, current)

    if not args.quiet:
        print(report.summary())

    if args.degraded_only and report.has_degradations:
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
