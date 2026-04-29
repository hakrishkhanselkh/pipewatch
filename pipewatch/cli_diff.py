"""CLI entry point for pipeline-diff: compare two result snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.pipeline_diff import PipelineDiffer
from pipewatch.snapshotter import _dict_to_result
from pipewatch.metrics import MetricResult


def _load_results(path: str) -> List[MetricResult]:
    data = json.loads(Path(path).read_text())
    if isinstance(data, list):
        return [_dict_to_result(d) for d in data]
    # Support snapshot format with a top-level "results" key
    return [_dict_to_result(d) for d in data.get("results", [])]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-diff",
        description="Compare two pipeline result snapshots and show what changed.",
    )
    parser.add_argument("before", help="Path to the baseline results JSON file")
    parser.add_argument("after", help="Path to the new results JSON file")
    parser.add_argument(
        "--show-unchanged",
        action="store_true",
        default=False,
        help="Also print metrics that have not changed",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output diff as JSON",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        default=False,
        help="Exit with code 1 if any differences are found",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        before = _load_results(args.before)
        after = _load_results(args.after)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    report = PipelineDiffer().diff(before, after)

    if args.json:
        rows = []
        for e in report.entries:
            if not args.show_unchanged and not (e.is_added or e.is_removed or e.is_changed):
                continue
            rows.append({
                "source": e.source,
                "metric": e.metric_name,
                "before": e.before.status.value if e.before else None,
                "after": e.after.status.value if e.after else None,
                "change": "added" if e.is_added else "removed" if e.is_removed else "changed" if e.is_changed else "same",
            })
        print(json.dumps(rows, indent=2))
    else:
        print(str(report))
        if args.show_unchanged:
            for e in report.unchanged:
                print(f"  {e}")

    if args.exit_code and report.has_differences():
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
