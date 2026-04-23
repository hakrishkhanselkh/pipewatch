"""CLI entry point: rank pipeline metric results by severity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.ranker import ResultRanker


def _load_results(path: str) -> List[MetricResult]:
    with open(path) as fh:
        raw = json.load(fh)
    results = []
    for item in raw:
        results.append(
            MetricResult(
                source=item["source"],
                name=item["name"],
                value=item.get("value"),
                status=MetricStatus(item["status"]),
                timestamp=item.get("timestamp"),
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-rank",
        description="Rank pipeline metric results by severity and value.",
    )
    parser.add_argument("results_file", help="Path to JSON results file")
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="N",
        help="Show only the top N results (default: all)",
    )
    parser.add_argument(
        "--status",
        choices=["ok", "warning", "critical"],
        default=None,
        help="Filter to a specific status before ranking",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = _load_results(args.results_file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error loading results: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.status:
        target = MetricStatus(args.status)
        results = [r for r in results if r.status == target]

    ranker = ResultRanker(results)
    ranked = ranker.top(args.top) if args.top else ranker.rank()

    if not ranked:
        print("No results to display.")
        return

    for item in ranked:
        print(item)


if __name__ == "__main__":  # pragma: no cover
    main()
