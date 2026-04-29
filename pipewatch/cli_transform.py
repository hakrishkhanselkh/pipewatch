"""CLI entry point for the result transformer."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from pipewatch.metrics import MetricResult, MetricStatus
from pipewatch.snapshotter import _dict_to_result, _result_to_dict
from pipewatch.transformer import ResultTransformer, TransformRule


def _load_results(path: str) -> List[MetricResult]:
    with open(path) as fh:
        data = json.load(fh)
    return [_dict_to_result(d) for d in data]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipewatch-transform",
        description="Apply field transformations to pipeline results.",
    )
    p.add_argument("file", help="JSON results file to transform")
    p.add_argument(
        "--clamp-negative",
        action="store_true",
        default=False,
        help="Replace negative metric values with 0.0",
    )
    p.add_argument(
        "--cap-value",
        type=float,
        default=None,
        metavar="MAX",
        help="Cap metric values at MAX",
    )
    p.add_argument(
        "--source",
        default=None,
        help="Restrict transformations to this source",
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Emit transformed results as JSON",
    )
    return p


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = _load_results(args.file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    transformer = ResultTransformer()

    source_filter = (
        (lambda r, s=args.source: r.metric.source == s)
        if args.source
        else (lambda r: True)
    )

    if args.clamp_negative:
        def _clamp(r: MetricResult) -> MetricResult:
            if r.value is not None and r.value < 0:
                from dataclasses import replace
                return replace(r, value=0.0)
            return r

        transformer.add_rule(
            TransformRule("clamp-negative", source_filter, _clamp)
        )

    if args.cap_value is not None:
        cap = args.cap_value

        def _cap(r: MetricResult, _cap=cap) -> MetricResult:
            if r.value is not None and r.value > _cap:
                from dataclasses import replace
                return replace(r, value=_cap)
            return r

        transformer.add_rule(
            TransformRule("cap-value", source_filter, _cap)
        )

    transformed, report = transformer.transform(results)

    if args.as_json:
        print(json.dumps([_result_to_dict(r) for r in transformed], indent=2))
    else:
        print(report)
        for r in transformed:
            print(f"  {r.metric.source}/{r.metric.name}  value={r.value}  status={r.status.value}")


if __name__ == "__main__":  # pragma: no cover
    main()
