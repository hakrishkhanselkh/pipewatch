"""CLI entry point for displaying profiling reports from exported metric results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipewatch.profiler import Profiler, ProfileReport


def _load_profile_data(path: str) -> ProfileReport:
    """Load timing data from a JSON file produced by a profiling run."""
    data = json.loads(Path(path).read_text())
    profiler = Profiler()
    for entry in data.get("entries", []):
        profiler.record(
            source=entry["source"],
            metric_name=entry["metric_name"],
            duration_seconds=float(entry["duration_seconds"]),
        )
    return profiler.report()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-profile",
        description="Display pipeline metric collection timing profiles.",
    )
    parser.add_argument("file", help="Path to profile JSON file.")
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of slowest entries to show (default: 5).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output raw entries as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = _load_profile_data(args.file)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        print(f"Error loading profile file: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        output = [
            {
                "source": e.source,
                "metric_name": e.metric_name,
                "duration_seconds": e.duration_seconds,
                "timestamp": e.timestamp,
            }
            for e in report.slowest(args.top)
        ]
        print(json.dumps(output, indent=2))
    else:
        print(report)
        print(f"\nTop {args.top} slowest:")
        for entry in report.slowest(args.top):
            print(f"  {entry}")


if __name__ == "__main__":
    main()
