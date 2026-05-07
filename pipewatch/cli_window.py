"""CLI entry point for sliding-window statistics over a results file."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import List

from pipewatch.metrics import Metric, MetricResult, MetricStatus
from pipewatch.windower import ResultWindower, WindowConfig


def _load_results(path: str) -> List[MetricResult]:
    with open(path) as fh:
        raw = json.load(fh)
    results = []
    for item in raw:
        m = Metric(source=item["source"], name=item["name"])
        ts = datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else None
        results.append(
            MetricResult(
                metric=m,
                value=item.get("value"),
                status=MetricStatus[item["status"].upper()],
                timestamp=ts,
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipewatch-window",
        description="Show sliding-window stats for pipeline metrics.",
    )
    p.add_argument("file", help="JSON results file to analyse")
    p.add_argument(
        "--window",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Window size in seconds (default: 60)",
    )
    p.add_argument(
        "--source",
        default=None,
        help="Filter output to a specific source",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit output as JSON",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = _load_results(args.file)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        cfg = WindowConfig(window_seconds=args.window)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    windower = ResultWindower(cfg)
    for r in results:
        windower.add(r)

    all_stats = windower.all_stats()
    if args.source:
        all_stats = [s for s in all_stats if s.source == args.source]

    if args.json:
        payload = [
            {
                "source": s.source,
                "name": s.name,
                "window_seconds": s.window_seconds,
                "count": s.count,
                "min": s.min_value,
                "max": s.max_value,
                "avg": s.avg_value,
                "ok": s.ok_count,
                "warning": s.warning_count,
                "critical": s.critical_count,
            }
            for s in all_stats
        ]
        print(json.dumps(payload, indent=2))
    else:
        for s in all_stats:
            print(s)


if __name__ == "__main__":
    main()
