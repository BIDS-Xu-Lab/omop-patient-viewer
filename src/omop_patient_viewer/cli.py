from __future__ import annotations

import argparse
from pathlib import Path

from .app import OmopPatientViewerApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Terminal OMOP patient viewer")
    parser.add_argument(
        "csv_dir",
        type=Path,
        help="Path to a directory containing standard OMOP CSV files",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    app = OmopPatientViewerApp(args.csv_dir.expanduser().resolve())
    app.run()
