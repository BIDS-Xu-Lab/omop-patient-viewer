from __future__ import annotations

import csv
from pathlib import Path

from .models import TableData

STANDARD_OMOP_TABLES = (
    "person",
    "visit_occurrence",
    "observation",
    "measurement",
    "drug_exposure",
    "procedure_occurrence",
    "condition_occurrence",
    "condition_era",
    "drug_era",
    "observation_period",
)


def discover_tables(csv_dir: Path) -> dict[str, Path]:
    table_paths: dict[str, Path] = {}
    for table_name in STANDARD_OMOP_TABLES:
        path = csv_dir / f"{table_name}.csv"
        if path.exists():
            table_paths[table_name] = path
    return table_paths


def load_tables(csv_dir: Path) -> dict[str, TableData]:
    if not csv_dir.exists() or not csv_dir.is_dir():
        raise FileNotFoundError(f"CSV directory does not exist: {csv_dir}")

    table_paths = discover_tables(csv_dir)
    if "person" not in table_paths:
        raise FileNotFoundError(f"Required OMOP table missing: {csv_dir / 'person.csv'}")

    tables: dict[str, TableData] = {}
    for table_name, path in table_paths.items():
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
            tables[table_name] = TableData(
                name=table_name,
                path=path,
                columns=list(reader.fieldnames or []),
                rows=rows,
            )
    return tables
