from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def export_outputs(
    records: list[dict[str, Any]],
    output_csv: Path,
    conflicts_df: pd.DataFrame,
    parsing_report: dict[str, Any],
    source_catalog: list[dict[str, Any]],
    cbr_catalog: list[dict[str, Any]],
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False)
    df.to_parquet(output_csv.with_suffix(".parquet"), index=False)
    conflicts_df.to_csv(output_csv.parent / "conflicts.csv", index=False)
    pd.DataFrame(source_catalog).to_csv(output_csv.parent / "source_catalog.csv", index=False)
    pd.DataFrame(cbr_catalog).to_csv(output_csv.parent / "cbr_confirmations.csv", index=False)
    (output_csv.parent / "parsing_report.json").write_text(
        json.dumps(parsing_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
