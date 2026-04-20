"""Tag-based labeling and filtering for MetricResults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set

from pipewatch.metrics import MetricResult


@dataclass
class TagIndex:
    """Maintains an index of results grouped by tag."""

    _index: Dict[str, List[MetricResult]] = field(default_factory=dict, init=False)

    def add(self, result: MetricResult, tags: Iterable[str]) -> None:
        """Associate *result* with each tag in *tags*."""
        for tag in tags:
            self._index.setdefault(tag, []).append(result)

    def get(self, tag: str) -> List[MetricResult]:
        """Return all results associated with *tag* (empty list if unknown)."""
        return list(self._index.get(tag, []))

    def all_tags(self) -> Set[str]:
        """Return the set of all known tags."""
        return set(self._index.keys())

    def __len__(self) -> int:
        return sum(len(v) for v in self._index.values())


class ResultTagger:
    """Attach and query string tags on MetricResults."""

    def __init__(self) -> None:
        self._tags: Dict[int, Set[str]] = {}  # keyed by id(result)
        self._index = TagIndex()

    def tag(self, result: MetricResult, *tags: str) -> None:
        """Attach one or more tags to *result*."""
        key = id(result)
        existing = self._tags.setdefault(key, set())
        new_tags = set(tags) - existing
        existing.update(new_tags)
        self._index.add(result, new_tags)

    def tags_for(self, result: MetricResult) -> Set[str]:
        """Return the set of tags attached to *result*."""
        return set(self._tags.get(id(result), set()))

    def by_tag(self, tag: str) -> List[MetricResult]:
        """Return all results that carry *tag*."""
        return self._index.get(tag)

    def by_all_tags(self, *tags: str) -> List[MetricResult]:
        """Return results that carry ALL of the supplied tags."""
        if not tags:
            return []
        sets = [set(self._index.get(t)) for t in tags]
        common = sets[0].intersection(*sets[1:])
        return list(common)

    def all_tags(self) -> Set[str]:
        """Return every tag that has been registered."""
        return self._index.all_tags()
