from __future__ import annotations

from collections import defaultdict

from .loader import STANDARD_OMOP_TABLES
from .models import PatientStats, TableData, VisitSummary

VISIT_TABLE = "visit_occurrence"
SUMMARY_TABLES = (
    "measurement",
    "observation",
    "drug_exposure",
    "procedure_occurrence",
    "condition_occurrence",
)
VISIT_LINKED_TABLES = (
    "measurement",
    "observation",
    "drug_exposure",
    "procedure_occurrence",
    "condition_occurrence",
)
PATIENT_LEVEL_TABLES = (
    "observation_period",
    "condition_era",
    "drug_era",
)


class OmopRepository:
    def __init__(self, tables: dict[str, TableData]) -> None:
        self.tables = tables
        self.table_names = [name for name in STANDARD_OMOP_TABLES if name in tables]
        self.rows_by_person: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.rows_by_visit: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.patient_stats: list[PatientStats] = []
        self._build_indexes()

    def _build_indexes(self) -> None:
        people = self.tables["person"].rows
        stats_by_person: dict[str, PatientStats] = {}
        for row in people:
            person_id = row.get("person_id", "")
            stats_by_person[person_id] = PatientStats(
                person_id=person_id,
                visit_count=0,
                event_count=0,
                table_counts={table: 0 for table in SUMMARY_TABLES},
            )
            self.rows_by_person["person"][person_id].append(row)

        for table_name, table in self.tables.items():
            if table_name == "person":
                continue
            for row in table.rows:
                person_id = row.get("person_id")
                if person_id:
                    self.rows_by_person[table_name][person_id].append(row)
                    stats = stats_by_person.get(person_id)
                    if stats and table_name in SUMMARY_TABLES:
                        stats.table_counts[table_name] += 1
                        stats.event_count += 1
                    if stats and table_name == VISIT_TABLE:
                        stats.visit_count += 1
                visit_id = row.get("visit_occurrence_id")
                if visit_id not in (None, "", "0"):
                    self.rows_by_visit[table_name][visit_id].append(row)

        self.patient_stats = sorted(stats_by_person.values(), key=lambda item: int(item.person_id or 0))

    def list_patients(self) -> list[PatientStats]:
        return self.patient_stats

    def get_person_row(self, person_id: str) -> dict[str, str] | None:
        rows = self.rows_by_person["person"].get(person_id, [])
        return rows[0] if rows else None

    def get_patient_summary_lines(self, person_id: str) -> list[str]:
        person = self.get_person_row(person_id)
        stats = next((item for item in self.patient_stats if item.person_id == person_id), None)
        if not person or not stats:
            return [f"Person {person_id} not found."]

        birth_parts = [
            person.get("year_of_birth", ""),
            person.get("month_of_birth", ""),
            person.get("day_of_birth", ""),
        ]
        birth = "-".join(part.zfill(2) if index else part for index, part in enumerate(birth_parts) if part)
        lines = [
            f"Person ID: {person_id}",
            f"Gender Concept: {person.get('gender_concept_id', '-')}",
            f"Birth: {birth or '-'}",
            f"Race Concept: {person.get('race_concept_id', '-')}",
            f"Ethnicity Concept: {person.get('ethnicity_concept_id', '-')}",
            f"Visits: {stats.visit_count}",
            f"Events: {stats.event_count}",
        ]
        counts = ", ".join(f"{table}={stats.table_counts[table]}" for table in SUMMARY_TABLES)
        lines.append(f"Event Counts: {counts}")
        return lines

    def get_patient_tables(self, person_id: str) -> list[str]:
        names: list[str] = []
        for table_name in self.table_names:
            if table_name == "person":
                names.append(table_name)
                continue
            if self.rows_by_person[table_name].get(person_id):
                names.append(table_name)
        return names

    def get_patient_rows(self, person_id: str, table_name: str) -> list[dict[str, str]]:
        return self.rows_by_person[table_name].get(person_id, [])

    def get_patient_visits(self, person_id: str) -> list[VisitSummary]:
        visits = self.rows_by_person[VISIT_TABLE].get(person_id, [])
        visit_summaries: list[VisitSummary] = []
        for row in sorted(
            visits,
            key=lambda item: (item.get("visit_start_date", ""), item.get("visit_occurrence_id", "")),
        ):
            visit_id = row.get("visit_occurrence_id", "")
            event_count = 0
            for table_name in VISIT_LINKED_TABLES:
                event_count += len(self.rows_by_visit[table_name].get(visit_id, []))
            visit_summaries.append(
                VisitSummary(
                    visit_occurrence_id=visit_id,
                    visit_start_date=row.get("visit_start_date", ""),
                    visit_end_date=row.get("visit_end_date", ""),
                    row=row,
                    event_count=event_count,
                )
            )
        return visit_summaries

    def get_visit_bundle(self, visit_id: str) -> dict[str, list[dict[str, str]]]:
        bundle: dict[str, list[dict[str, str]]] = {}
        for table_name in VISIT_LINKED_TABLES:
            bundle[table_name] = self.rows_by_visit[table_name].get(visit_id, [])
        return bundle

    def get_unlinked_patient_records(self, person_id: str) -> dict[str, list[dict[str, str]]]:
        return {
            table_name: self.rows_by_person[table_name].get(person_id, [])
            for table_name in PATIENT_LEVEL_TABLES
            if self.rows_by_person[table_name].get(person_id, [])
        }
