"""CLI entry-point: partition pipeline results into named buckets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.partitioner import ResultPartitioner
from pipewatch.snapshotter import _dict_to_result


def _load_results(path: str) -> List[MetricResult]:
    data = json.loads(Path(path).read_text())
    return [_dict_to_result(d) for d in data]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipewatch-partition",
        description="Partition pipeline results into named buckets.",
    )
    p.add_argument("file", help="JSON results file produced by pipewatch export.")
    p.add_argument(
        "--by",
        choices=["status", "source"],
        default="status",
        help="Dimension to partition by (default: status).",
    )
    p.add_argument(
        "--default-bucket",
        default="other",
        metavar="NAME",
        help="Bucket name for unmatched results (default: other).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit partition counts as JSON.",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        results = _load_results(args.file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    partitioner = ResultPartitioner(default_bucket=args.default_bucket)

    if args.by == "status":
        for status in (MetricStatus.CRITICAL, MetricStatus.WARNING, MetricStatus.OK):
            partitioner.add_rule(status.value, lambda r, s=status: r.status == s)
    else:
        sources = sorted({r.metric.source for r in results})
        for src in sources:
            partitioner.add_rule(src, lambda r, s=src: r.metric.source == s)

    report = partitioner.partition(results)

    if args.json:
        out = {name: len(p) for name, p in report.partitions.items()}
        out["unmatched"] = len(report.unmatched)
        print(json.dumps(out, indent=2))
    else:
        print(str(report))
        for name, part in report.partitions.items():
            print(f"  {name}: {len(part)} result(s)")
        if report.unmatched:
            print(f"  unmatched: {len(report.unmatched)} result(s)")


if __name__ == "__main__":  # pragma: no cover
    main()
