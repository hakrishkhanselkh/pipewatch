"""CLI entry-point for snapshot save / load / list operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipewatch.snapshotter import Snapshotter
from pipewatch.metrics import MetricResult


def _load_results(path: str):
    """Load MetricResults from a JSON file produced by cli_export."""
    from pipewatch.exporters import _result_to_dict  # noqa: F401 – reuse shape
    from pipewatch.snapshotter import _dict_to_result

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [_dict_to_result(item) for item in raw]
    # Support snapshot envelope format too
    return [_dict_to_result(item) for item in raw.get("results", [])]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-snapshot",
        description="Save, load, or list pipeline metric snapshots.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    save_p = sub.add_parser("save", help="Save results to a snapshot file.")
    save_p.add_argument("results", help="Path to JSON results file.")
    save_p.add_argument("--dir", default=".", help="Directory to store snapshots.")
    save_p.add_argument("--label", default=None, help="Optional label for the file.")

    load_p = sub.add_parser("load", help="Print contents of a snapshot file.")
    load_p.add_argument("snapshot", help="Path to snapshot file.")

    list_p = sub.add_parser("list", help="List available snapshots in a directory.")
    list_p.add_argument("--dir", default=".", help="Directory to search.")

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    snapshotter = Snapshotter(directory=getattr(args, "dir", "."))

    if args.command == "save":
        results = _load_results(args.results)
        path = snapshotter.save(results, label=args.label)
        print(f"Snapshot saved: {path}")

    elif args.command == "load":
        results = snapshotter.load(args.snapshot)
        for r in results:
            print(r)

    elif args.command == "list":
        files = snapshotter.list_snapshots()
        if not files:
            print("No snapshots found.")
        for f in files:
            print(f)


if __name__ == "__main__":  # pragma: no cover
    main()
