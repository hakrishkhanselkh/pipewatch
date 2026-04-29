"""Archive MetricResults to timestamped files for long-term storage."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pipewatch.metrics import MetricResult
from pipewatch.snapshotter import _result_to_dict, _dict_to_result


@dataclass
class ArchiveEntry:
    label: str
    archived_at: datetime
    path: Path
    result_count: int

    def __str__(self) -> str:
        ts = self.archived_at.strftime("%Y-%m-%dT%H:%M:%S")
        return f"[{ts}] {self.label} — {self.result_count} result(s) → {self.path}"


@dataclass
class Archiver:
    archive_dir: Path
    _entries: List[ArchiveEntry] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.archive_dir = Path(self.archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive(
        self,
        results: List[MetricResult],
        label: Optional[str] = None,
        *,
        now: Optional[datetime] = None,
    ) -> ArchiveEntry:
        """Persist *results* to a JSON file and return an ArchiveEntry."""
        ts = now or datetime.now(timezone.utc)
        slug = ts.strftime("%Y%m%dT%H%M%S")
        safe_label = (label or "archive").replace(" ", "_")
        filename = f"{slug}_{safe_label}.json"
        dest = self.archive_dir / filename

        payload = {
            "label": safe_label,
            "archived_at": ts.isoformat(),
            "results": [_result_to_dict(r) for r in results],
        }
        dest.write_text(json.dumps(payload, indent=2))

        entry = ArchiveEntry(
            label=safe_label,
            archived_at=ts,
            path=dest,
            result_count=len(results),
        )
        self._entries.append(entry)
        return entry

    def load(self, path: Path) -> List[MetricResult]:
        """Deserialise results from a previously archived file."""
        data = json.loads(Path(path).read_text())
        return [_dict_to_result(r) for r in data["results"]]

    def list_archives(self) -> List[ArchiveEntry]:
        """Return all ArchiveEntry objects recorded in this session."""
        return list(self._entries)

    def purge_before(self, cutoff: datetime) -> int:
        """Delete archived files whose timestamp is before *cutoff*.

        Returns the number of files deleted.
        """
        removed = 0
        for entry in list(self._entries):
            if entry.archived_at < cutoff:
                try:
                    os.remove(entry.path)
                except FileNotFoundError:
                    pass
                self._entries.remove(entry)
                removed += 1
        return removed
