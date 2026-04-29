"""Result transformer: apply field-level transformations to MetricResults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from pipewatch.metrics import MetricResult


TransformFn = Callable[[MetricResult], MetricResult]


@dataclass
class TransformRule:
    """A named transformation applied to matching results."""

    name: str
    predicate: Callable[[MetricResult], bool]
    transform: TransformFn

    def applies_to(self, result: MetricResult) -> bool:
        return self.predicate(result)

    def apply(self, result: MetricResult) -> MetricResult:
        return self.transform(result)

    def __str__(self) -> str:
        return f"TransformRule({self.name!r})"


@dataclass
class TransformReport:
    """Summary of a transformation pass."""

    total: int = 0
    transformed: int = 0
    rules_applied: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"TransformReport(total={self.total}, "
            f"transformed={self.transformed}, "
            f"rules={self.rules_applied})"
        )


class ResultTransformer:
    """Applies a chain of TransformRules to a list of MetricResults."""

    def __init__(self) -> None:
        self._rules: List[TransformRule] = []

    def add_rule(self, rule: TransformRule) -> None:
        self._rules.append(rule)

    def transform(
        self, results: List[MetricResult]
    ) -> tuple[List[MetricResult], TransformReport]:
        report = TransformReport(total=len(results))
        output: List[MetricResult] = []
        rules_seen: set[str] = set()

        for result in results:
            current = result
            changed = False
            for rule in self._rules:
                if rule.applies_to(current):
                    current = rule.apply(current)
                    changed = True
                    rules_seen.add(rule.name)
            output.append(current)
            if changed:
                report.transformed += 1

        report.rules_applied = sorted(rules_seen)
        return output, report

    def rule_count(self) -> int:
        return len(self._rules)
