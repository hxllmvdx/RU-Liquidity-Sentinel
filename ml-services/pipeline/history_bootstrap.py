from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.build_wide_dataset import build_wide_lsi_dataset, repo_root
from pipeline.lsi_history import build_and_persist_lsi_history

logger = logging.getLogger(__name__)

DEFAULT_START_DATE = date(2021, 1, 1)
NOTEBOOK_PIPELINE: list[str] = []


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    return date.fromisoformat(value)


def _processed_csv_count() -> int:
    root = repo_root()
    return len([
        p for p in (root / "data" / "processed").glob("**/*.csv")
        if "/dashboard/" not in p.as_posix() and "/snapshots/" not in p.as_posix()
    ])


def _existing_history_rows() -> int:
    try:
        from common.database import Database
        db = Database()
        db.connect()
        try:
            row = db.fetch_one("SELECT COUNT(*) AS cnt FROM lsi_values")
            return int((row or {}).get("cnt", 0) or 0)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to count lsi_values rows: %s", exc)
        return 0


def _run_historical_parsers(date_from: date, date_to: date) -> list[dict[str, Any]]:
    from common.database import Database
    from ingestion.base_parser import BaseParser

    db = None
    try:
        db = Database()
        db.connect()
    except Exception as exc:
        logger.warning("Historical parser DB connection unavailable, running parsers without DB: %s", exc)
        db = None

    try:
        results = BaseParser.run_historical_mode(date_from=date_from, date_to=date_to, db=db, out_dir=repo_root() / "data" / "raw")
        return [
            {
                "source_code": r.source_code,
                "status": r.status,
                "record_count": r.record_count,
                "requested_from": str(r.requested_from) if r.requested_from else None,
                "requested_to": str(r.requested_to) if r.requested_to else None,
                "latest_observation_date": str(r.latest_observation_date) if r.latest_observation_date else None,
                "error": r.error,
            }
            for r in results
        ]
    finally:
        if db is not None:
            db.close()


def _run_processing_scripts() -> list[dict[str, Any]]:
    return [
        {
            "stage": "production_builders",
            "status": "skipped_notebook_pipeline",
            "reason": "bootstrap now uses production dataset builders; notebook scripts are not runtime dependencies",
        }
    ]


def bootstrap_full_history(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    persist: bool = True,
    run_historical_parsers: bool | None = None,
    run_processing_scripts: bool | None = None,
) -> dict[str, Any]:
    """Build and persist full LSI history from real parsers + processed data.

    This bootstrap intentionally does not accept a one-row latest snapshot as
    historical data. For production startup the default behavior is:
    1. inspect existing processed CSV history;
    2. if it is shorter than RLS_BOOTSTRAP_MIN_HISTORY_ROWS, run all BaseParser
       historical parsers for RLS_BOOTSTRAP_HISTORY_FROM..today;
    3. run notebook-style processors to convert raw data into processed module CSVs;
    4. backfill LSI/SHAP/contributions/flags into PostgreSQL and dashboard CSV.
    """
    date_from = date_from or _parse_date(os.getenv("RLS_BOOTSTRAP_HISTORY_FROM"), DEFAULT_START_DATE)
    date_to = date_to or datetime.now(timezone.utc).date()
    run_historical_parsers = _bool_env("RLS_BOOTSTRAP_RUN_HISTORICAL_PARSERS", True) if run_historical_parsers is None else run_historical_parsers
    run_processing_scripts = _bool_env("RLS_BOOTSTRAP_RUN_PROCESSING_SCRIPTS", True) if run_processing_scripts is None else run_processing_scripts
    force_historical = _bool_env("RLS_BOOTSTRAP_FORCE_HISTORICAL_PARSERS", True)
    min_history_rows = int(os.getenv("RLS_BOOTSTRAP_MIN_HISTORY_ROWS", "1000"))

    first_rows = _existing_history_rows()
    if first_rows >= min_history_rows and not force_historical:
        wide = build_wide_lsi_dataset(date_from=date_from.isoformat(), date_to=date_to.isoformat(), persist_csv=True)
        built = build_and_persist_lsi_history(persist=persist)
        return {
            "stage": "processed_existing",
            **built,
            "processed_csv_count": _processed_csv_count(),
            "min_history_rows": min_history_rows,
            "db_history_rows": first_rows,
            "historical_parsers_skipped": True,
        }

    parser_results: list[dict[str, Any]] = []
    processor_results: list[dict[str, Any]] = []

    if run_historical_parsers:
        logger.info(
            "Processed history has only %s rows; running BaseParser historical mode for %s..%s",
            first_rows,
            date_from,
            date_to,
        )
        parser_results = _run_historical_parsers(date_from, date_to)

    if run_processing_scripts:
        logger.info("Running processing scripts after historical parser bootstrap")
        processor_results = _run_processing_scripts()

    wide = build_wide_lsi_dataset(date_from=date_from.isoformat(), date_to=date_to.isoformat(), persist_csv=True)
    second = build_and_persist_lsi_history(persist=persist)
    return {
        "stage": "historical_bootstrap",
        **second,
        "initial_rows": first_rows,
        "processed_csv_count": _processed_csv_count(),
        "wide_dataset_rows": int(len(wide)),
        "min_history_rows": min_history_rows,
        "force_historical": force_historical,
        "parser_results": parser_results,
        "processor_results": processor_results,
    }


def run_history_bootstrap(
    date_from: str = "2021-01-01",
    date_to: str | None = None,
    force_historical_parsers: bool = True,
    run_processing: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    return bootstrap_full_history(
        date_from=date.fromisoformat(date_from),
        date_to=_parse_date(date_to, datetime.now(timezone.utc).date()) if date_to else None,
        persist=persist,
        run_historical_parsers=force_historical_parsers,
        run_processing_scripts=run_processing,
    )


def main() -> None:
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(json.dumps(bootstrap_full_history(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
