"""CLI entry-point: filter a results file through the throttler.

Usage examples
--------------
  pipewatch-throttle results.json --max 5 --window 30
  pipewatch-throttle results.json --max 5 --window 30 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.throttler import Throttler, ThrottleConfig


def _load_results(path: str) -> List[MetricResult]:
    raw = json.loads(Path(path).read_text())
    results: List[MetricResult] = []
    for item in raw:
        results.append(
            MetricResult(
                source=item["source"],
                name=item["name"],
                value=item["value"],
                status=MetricStatus[item["status"]],
                timestamp=item.get("timestamp"),
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipewatch-throttle",
        description="Rate-limit metric results per source.",
    )
    p.add_argument("file", help="JSON results file to read")
    p.add_argument(
        "--max",
        type=int,
        default=10,
        dest="max_per_window",
        metavar="N",
        help="Maximum results per source per window (default: 10)",
    )
    p.add_argument(
        "--window",
        type=float,
        default=60.0,
        dest="window_seconds",
        metavar="SECS",
        help="Rolling window size in seconds (default: 60)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit allowed results as JSON",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    try:
        config = ThrottleConfig(
            max_per_window=args.max_per_window,
            window_seconds=args.window_seconds,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    results = _load_results(args.file)
    throttler = Throttler(config)
    allowed = throttler.filter(results)

    sources = {r.source for r in results}
    total_dropped = sum(throttler.dropped_count(s) for s in sources)

    if args.json:
        output = [
            {
                "source": r.source,
                "name": r.name,
                "value": r.value,
                "status": r.status.name,
                "timestamp": r.timestamp,
            }
            for r in allowed
        ]
        print(json.dumps(output, indent=2))
    else:
        print(f"Allowed : {len(allowed)}")
        print(f"Dropped : {total_dropped}")
        for src in sorted(sources):
            d = throttler.dropped_count(src)
            if d:
                print(f"  {src}: dropped {d}")


if __name__ == "__main__":  # pragma: no cover
    main()
