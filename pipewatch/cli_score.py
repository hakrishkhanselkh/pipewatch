"""CLI entry-point: pipewatch-score — print a health score for a results file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.scorer import ResultScorer


def _load_results(path: str) -> List[MetricResult]:
    data = json.loads(Path(path).read_text())
    results: List[MetricResult] = []
    for item in data:
        results.append(
            MetricResult(
                source=item["source"],
                name=item["name"],
                value=item.get("value"),
                status=MetricStatus(item["status"]),
                message=item.get("message", ""),
            )
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewatch-score",
        description="Compute a health score (0–100) for pipeline metric results.",
    )
    parser.add_argument("file", help="JSON results file produced by pipewatch-export")
    parser.add_argument(
        "--warning-weight",
        type=float,
        default=0.5,
        metavar="W",
        help="Penalty weight for WARNING results (default: 0.5)",
    )
    parser.add_argument(
        "--critical-weight",
        type=float,
        default=1.0,
        metavar="W",
        help="Penalty weight for CRITICAL results (default: 1.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output score report as JSON",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        metavar="N",
        help="Exit with code 1 if score is below N (default: 0 — never fail)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = _load_results(args.file)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    scorer = ResultScorer(
        warning_weight=args.warning_weight,
        critical_weight=args.critical_weight,
    )
    report = scorer.score(results)

    if args.json:
        print(
            json.dumps(
                {
                    "score": report.score,
                    "grade": report.grade,
                    "total": report.total,
                    "ok": report.ok_count,
                    "warning": report.warning_count,
                    "critical": report.critical_count,
                },
                indent=2,
            )
        )
    else:
        print(report)

    if report.score < args.min_score:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
