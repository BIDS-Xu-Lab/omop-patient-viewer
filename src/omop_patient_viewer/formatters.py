from __future__ import annotations

from collections.abc import Iterable


SUMMARY_PREFERRED_FIELDS = (
    "person_id",
    "visit_occurrence_id",
    "visit_start_date",
    "visit_end_date",
    "measurement_date",
    "measurement_source_value",
    "observation_date",
    "observation_source_value",
    "drug_exposure_start_date",
    "drug_source_value",
    "procedure_date",
    "procedure_source_value",
    "condition_start_date",
    "condition_source_value",
    "condition_era_start_date",
    "condition_concept_id",
    "drug_era_start_date",
    "drug_concept_id",
    "observation_period_start_date",
    "observation_period_end_date",
)


def summarize_row(row: dict[str, str], limit: int = 5) -> str:
    fields: list[str] = []
    used: set[str] = set()

    for key in SUMMARY_PREFERRED_FIELDS:
        value = row.get(key)
        if value not in ("", None):
            fields.append(f"{key}={value}")
            used.add(key)
        if len(fields) >= limit:
            return " | ".join(fields)

    for key, value in row.items():
        if key in used or value in ("", None):
            continue
        fields.append(f"{key}={value}")
        if len(fields) >= limit:
            break

    return " | ".join(fields) if fields else "<empty record>"


def format_record(row: dict[str, str], expanded: bool) -> str:
    if not expanded:
        return summarize_row(row)
    return "\n".join(f"{key}: {value}" for key, value in row.items())


def without_keys(row: dict[str, str], keys: set[str]) -> dict[str, str]:
    return {key: value for key, value in row.items() if key not in keys}


def join_lines(lines: Iterable[str]) -> str:
    return "\n".join(lines)
