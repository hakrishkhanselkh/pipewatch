"""CLI entry-point for the archiver: save / load / list / purge."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipewatch.archiver import Archiver
from pipewatch.snapshotter import _dict_to_result


def _load_results(path: str):
    data = json.loads(Path(path).read_text())
    if isinstance(data, list):
        return [_dict_to_result(r) for r in data]
    # Support snapshot-style envelopes
    return [_dict_to_result(r) for r in data.get("results", [])]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-archive",
        description="Archive pipeline results for long-term storage.",
    )
    parser.add_argument(
        "--archive-dir",
        default=".pipewatch_archives",
        metavar="DIR",
        help="Directory used to store archive files (default: .pipewatch_archives).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # save
    save_p = sub.add_parser("save", help="Archive results from a JSON file.")
    save_p.add_argument("file", help="Path to results JSON file.")
    save_p.add_argument("--label", default="archive", help="Human-readable label.")

    # load
    load_p = sub.add_parser("load", help="Print results from an archive file.")
    load_p.add_argument("file", help="Path to archive JSON file.")

    # purge
    purge_p = sub.add_parser("purge", help="Delete archives older than N days.")
    purge_p.add_argument(
        "--days", type=int, default=30, help="Remove archives older than this many days."
    )

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    archiver = Archiver(archive_dir=args.archive_dir)

    if args.command == "save":
        results = _load_results(args.file)
        entry = archiver.archive(results, label=args.label)
        print(f"Archived {entry.result_count} result(s) → {entry.path}")

    elif args.command == "load":
        results = archiver.load(Path(args.file))
        for r in results:
            status = r.status.value if hasattr(r.status, "value") else r.status
            print(f"{r.source}/{r.metric_name}: {r.value} [{status}]")

    elif args.command == "purge":
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
        removed = archiver.purge_before(cutoff)
        print(f"Purged {removed} archive(s) older than {args.days} day(s).")

    else:  # pragma: no cover
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
