"""CLI entry point: manage and inspect silence rules for pipewatch."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from pipewatch.silencer import Silencer, SilenceRule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-silence",
        description="Add or list silence rules that suppress pipeline alerts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- add subcommand ---
    add_p = sub.add_parser("add", help="Add a new silence rule.")
    add_p.add_argument("--source", default=None, help="Source name to silence.")
    add_p.add_argument("--metric", default=None, help="Metric name to silence.")
    add_p.add_argument(
        "--duration",
        type=float,
        default=None,
        metavar="SECONDS",
        help="How long the rule is active (omit for permanent).",
    )
    add_p.add_argument("--reason", default="", help="Human-readable reason.")
    add_p.add_argument(
        "--rules-file",
        default="silence_rules.json",
        help="JSON file to persist rules (default: silence_rules.json).",
    )

    # --- list subcommand ---
    list_p = sub.add_parser("list", help="List active silence rules.")
    list_p.add_argument(
        "--rules-file",
        default="silence_rules.json",
        help="JSON file containing persisted rules.",
    )

    return parser


def _load_rules(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as fh:
        return json.load(fh)


def _save_rules(path: Path, rules: list[dict]) -> None:
    with path.open("w") as fh:
        json.dump(rules, fh, indent=2)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    rules_path = Path(args.rules_file)

    if args.command == "add":
        if args.source is None and args.metric is None:
            parser.error("At least one of --source or --metric is required.")

        expires_at = (time.time() + args.duration) if args.duration else None
        rule = SilenceRule(
            source=args.source,
            metric_name=args.metric,
            expires_at=expires_at,
            reason=args.reason,
        )

        raw = _load_rules(rules_path)
        raw.append(
            {
                "source": rule.source,
                "metric_name": rule.metric_name,
                "expires_at": rule.expires_at,
                "reason": rule.reason,
            }
        )
        _save_rules(rules_path, raw)
        print(f"Rule added: {rule}")

    elif args.command == "list":
        raw = _load_rules(rules_path)
        silencer = Silencer()
        for entry in raw:
            silencer.add_rule(
                SilenceRule(
                    source=entry.get("source"),
                    metric_name=entry.get("metric_name"),
                    expires_at=entry.get("expires_at"),
                    reason=entry.get("reason", ""),
                )
            )
        active = silencer.active_rules()
        if not active:
            print("No active silence rules.")
        else:
            for rule in active:
                print(rule)


if __name__ == "__main__":  # pragma: no cover
    main()
