from __future__ import annotations

import asyncio
from pathlib import Path

from omop_patient_viewer.app import OmopPatientViewerApp
from omop_patient_viewer.loader import load_tables
from omop_patient_viewer.repository import OmopRepository


def test_repository_loads_sample_data() -> None:
    repo = OmopRepository(load_tables(Path("sample_omop_data")))
    patients = repo.list_patients()
    assert patients
    assert patients[0].person_id == "1"
    assert "visit_occurrence" in repo.get_patient_tables("1")
    assert repo.get_patient_visits("1")


def test_app_smoke() -> None:
    async def _run() -> None:
        app = OmopPatientViewerApp(Path("sample_omop_data").resolve())
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_person_id == "1"
            await pilot.press("v")
            await pilot.pause()
            assert app.current_view_mode == "visit"

    asyncio.run(_run())
