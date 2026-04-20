"""CLI entry-point: tag results from a JSON export and query by tag."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.tagger import ResultTagger


def _load_results(path: str) -> List[MetricResult]:
    with open(path) as fh:
        data = json.load(fh)
    results: List[MetricResult] = []
    for item in data:
        results.append(
            MetricResult(
                source=item["source"],
                name=item["name"],
                value=item["value"],
                status=MetricStatus[item["status"].upper()],
                message=item.get("message", ""),
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-tag",
        description="Tag pipeline results and filter by tag.",
    )
    parser.add_argument("input", help="Path to JSON export file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tag_p = subparsers.add_parser("tag", help="Assign tags based on status")
    tag_p.add_argument("--warning", nargs="*", default=[], metavar="TAG",
                       help="Tags to apply to WARNING results")
    tag_p.add_argument("--critical", nargs="*", default=[], metavar="TAG",
                       help="Tags to apply to CRITICAL results")
    tag_p.add_argument("--ok", nargs="*", default=[], metavar="TAG",
                       help="Tags to apply to OK results")

    query_p = subparsers.add_parser("query", help="List results with given tag(s)")
    query_p.add_argument("tags", nargs="+", help="Tags to filter by (AND logic)")

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    results = _load_results(args.input)
    tagger = ResultTagger()

    status_tag_map = {}
    if args.command == "tag":
        status_tag_map = {
            MetricStatus.OK: args.ok,
            MetricStatus.WARNING: args.warning,
            MetricStatus.CRITICAL: args.critical,
        }
        for result in results:
            extra_tags = status_tag_map.get(result.status, [])
            if extra_tags:
                tagger.tag(result, *extra_tags)
        print(f"Tagged {len(results)} result(s). Known tags: {sorted(tagger.all_tags())}")

    elif args.command == "query":
        for result in results:
            tagger.tag(result, result.source, result.status.value.lower())
        matched = tagger.by_all_tags(*args.tags)
        if not matched:
            print("No results matched.")
            sys.exit(0)
        for r in matched:
            print(f"[{r.status.value}] {r.source}/{r.name} = {r.value}  {r.message}")


if __name__ == "__main__":  # pragma: no cover
    main()
