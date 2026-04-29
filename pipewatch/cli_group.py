"""CLI entry-point: group pipeline results and display per-group summaries."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.metrics import MetricResult
from pipewatch.snapshotter import Snapshotter
from pipewatch.grouper import ResultGrouper


def _load_results(path: str) -> List[MetricResult]:
    s = Snapshotter(Path(path))
    snap = s.load()
    if snap is None:
        print(f"error: no snapshot found at {path}", file=sys.stderr)
        sys.exit(1)
    return snap.results


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipewatch-group",
        description="Group pipeline metric results and show per-group summaries.",
    )
    p.add_argument("file", help="Path to snapshot JSON file")
    p.add_argument(
        "--by",
        choices=["source", "status", "name"],
        default="source",
        help="Field to group by (default: source)",
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Emit output as JSON",
    )
    p.add_argument(
        "--min-count",
        type=int,
        default=1,
        metavar="N",
        help="Only show groups with at least N results (default: 1)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    results = _load_results(args.file)

    key_fns = {
        "source": lambda r: r.metric.source,
        "status": lambda r: r.status.value,
        "name": lambda r: r.metric.name,
    }
    grouper = ResultGrouper(key_fn=key_fns[args.by])
    grouper.add_all(results)

    groups = [
        g for g in grouper.all_groups() if g.count >= args.min_count
    ]
    groups.sort(key=lambda g: g.key)

    if args.as_json:
        payload = [
            {
                "key": g.key,
                "count": g.count,
                "ok": g.ok_count,
                "warning": g.warning_count,
                "critical": g.critical_count,
                "worst_status": g.worst_status.value,
            }
            for g in groups
        ]
        print(json.dumps(payload, indent=2))
    else:
        if not groups:
            print("No groups match the given criteria.")
            return
        for g in groups:
            print(str(g))


if __name__ == "__main__":  # pragma: no cover
    main()
