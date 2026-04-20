"""CLI entry-point: replay a JSON export and display metric trends."""

import argparse
import json
import sys
from pathlib import Path

from pipewatch.exporters import _result_to_dict  # noqa: F401 (for reference)
from pipewatch.history import MetricHistory
from pipewatch.metrics import Metric, MetricResult, MetricStatus


# ---------------------------------------------------------------------------
def _load_results(path: str) -> list:
    """Parse a JSON file produced by JsonExporter into MetricResult objects."""
    data = json.loads(Path(path).read_text())
    results = []
    for item in data:
        metric = Metric(
            name=item["name"],
            source=item["source"],
            value=item["value"],
        )
        result = MetricResult(
            metric=metric,
            status=MetricStatus[item["status"]],
            message=item.get("message", ""),
        )
        results.append(result)
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-history",
        description="Show metric trends from one or more JSON export files.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="JSON export files to load (in chronological order).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        metavar="N",
        help="Number of recent samples to use for trend detection (default: 5).",
    )
    parser.add_argument(
        "--source",
        default=None,
        metavar="SRC",
        help="Filter output to a specific source.",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    history = MetricHistory(maxlen=max(args.window * 2, 20))

    for fpath in args.files:
        try:
            results = _load_results(fpath)
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
            print(f"ERROR loading {fpath}: {exc}", file=sys.stderr)
            return 1
        history.record_all(results)

    trends = history.all_trends(window=args.window)
    if args.source:
        trends = [t for t in trends if t.source == args.source]

    if not trends:
        print("No trend data available.")
        return 0

    for trend in sorted(trends, key=lambda t: (t.source, t.name)):
        print(trend)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
