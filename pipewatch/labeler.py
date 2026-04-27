"""Labeler: attach arbitrary key-value labels to MetricResults for downstream grouping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from pipewatch.metrics import MetricResult


@dataclass
class LabeledResult:
    """A MetricResult decorated with a set of labels."""

    result: MetricResult
    labels: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or None if absent."""
        return self.labels.get(key)

    def __str__(self) -> str:  # pragma: no cover
        label_str = ", ".join(f"{k}={v}" for k, v in sorted(self.labels.items()))
        return f"LabeledResult({self.result.name} [{label_str}])"


class Labeler:
    """Attach and query labels on MetricResults.

    Labels are simple string key-value pairs (e.g. env=prod, team=data).
    """

    def __init__(self) -> None:
        # fingerprint -> LabeledResult  (fingerprint = id(result) for identity)
        self._store: Dict[int, LabeledResult] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def label(self, result: MetricResult, **labels: str) -> LabeledResult:
        """Attach *labels* to *result*, merging with any existing labels."""
        key = id(result)
        if key not in self._store:
            self._store[key] = LabeledResult(result=result)
        self._store[key].labels.update(labels)
        return self._store[key]

    def label_many(
        self, results: Iterable[MetricResult], **labels: str
    ) -> List[LabeledResult]:
        """Convenience: label an iterable of results with the same labels."""
        return [self.label(r, **labels) for r in results]

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, result: MetricResult) -> Optional[LabeledResult]:
        """Return the LabeledResult for *result*, or None if unlabeled."""
        return self._store.get(id(result))

    def find_by_label(self, key: str, value: str) -> List[LabeledResult]:
        """Return all LabeledResults where labels[key] == value."""
        return [
            lr for lr in self._store.values() if lr.labels.get(key) == value
        ]

    def all_labeled(self) -> List[LabeledResult]:
        """Return every LabeledResult currently tracked."""
        return list(self._store.values())

    def __len__(self) -> int:
        return len(self._store)
