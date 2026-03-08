from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class TableData:
    name: str
    path: Path
    columns: list[str]
    rows: list[dict[str, str]]


@dataclass(slots=True)
class PatientStats:
    person_id: str
    visit_count: int
    event_count: int
    table_counts: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class VisitSummary:
    visit_occurrence_id: str
    visit_start_date: str
    visit_end_date: str
    row: dict[str, str]
    event_count: int
