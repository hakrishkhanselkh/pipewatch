"""CLI entry-point: aggregate exported JSON results and print statistics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipewatch.aggregator import ResultAggregator
from pipewatch.metrics import Metric, MetricResult, MetricStatus


def _load_results(path: str) -> list:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValueError("JSON file must contain a top-level array of results.")
    return data


def _parse_result(obj: dict) -> MetricResult:
    metric = Metric(
        name=obj["name"],
        source=obj["source"],
        value=float(obj["value"]),
    )
    return MetricResult(
        metric=metric,
        value=float(obj["value"]),
        status=MetricStatus(obj["status"]),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-aggregate",
        description="Aggregate pipeline metric results and display statistics.",
    )
    parser.add_argument(
        "file",
        nargs="+",
        help="One or more JSON result files produced by pipewatch-export.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Filter output to a specific source name.",
    )
    parser.add_argument(
        "--metric",
        default=None,
        help="Filter output to a specific metric name.",
    )
    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    aggregator = ResultAggregator()

    for filepath in args.file:
        try:
            raw = _load_results(filepath)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR loading {filepath}: {exc}", file=sys.stderr)
            sys.exit(1)
        for obj in raw:
            try:
                aggregator.add(_parse_result(obj))
            except (KeyError, ValueError):
                pass  # skip malformed records

    all_stats = aggregator.all_stats()

    if args.source:
        all_stats = [s for s in all_stats if s.source == args.source]
    if args.metric:
        all_stats = [s for s in all_stats if s.name == args.metric]

    if not all_stats:
        print("No matching results found.")
        return

    for stat in sorted(all_stats, key=lambda s: (s.source, s.name)):
        print(stat)


if __name__ == "__main__":  # pragma: no cover
    main()
