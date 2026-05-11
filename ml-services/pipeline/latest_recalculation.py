from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import pandas as pd

from common.db_models import LSIResult
from lsi_engine.formula import calculate_lsi_from_snapshot
from pipeline.latest_snapshot import build_latest_snapshot, repo_root

DASHBOARD_DIR = repo_root() / "data" / "processed" / "dashboard"
SNAPSHOT_DIR = repo_root() / "data" / "processed" / "snapshots"

MODULE_IDS = {"M1": "M1_RESERVES", "M2": "M2_REPO", "M3": "M3_OFZ", "M4": "M4_TAX", "M5": "M5_TREASURY"}


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _save_csv_outputs(snapshot: dict[str, Any], result) -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([snapshot]).to_csv(SNAPSHOT_DIR / "latest_snapshot.csv", index=False)
    row = {
        "date": snapshot["date"],
        "LSI": result.lsi,
        "status": result.status,
        "confidence": result.confidence,
        "M1_score": result.module_scores.get("M1", 0.0),
        "M2_score": result.module_scores.get("M2", 0.0),
        "M3_score": result.module_scores.get("M3", 0.0),
        "M4_Seasonal_Factor": result.module_scores.get("M4_Seasonal_Factor", 1.0),
        "M5_score": result.module_scores.get("M5", 0.0),
        "M1_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M1"), 0.0),
        "M2_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M2"), 0.0),
        "M3_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M3"), 0.0),
        "M4_effect": result.module_scores.get("M4_Seasonal_Factor", 1.0),
        "M5_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M5"), 0.0),
    }
    lsi_path = DASHBOARD_DIR / "lsi_dashboard.csv"
    history = pd.read_csv(lsi_path) if lsi_path.exists() else pd.DataFrame()
    history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
    history = history.drop_duplicates(subset=["date"], keep="last").sort_values("date")
    history.to_csv(lsi_path, index=False)

    for module in ["m1", "m2", "m3", "m4", "m5"]:
        prefix = module.upper()
        data = {"date": snapshot["date"], "source_date": snapshot.get(f"{prefix}_date"), "status": snapshot.get(f"{prefix}_status")}
        data.update({k: v for k, v in snapshot.items() if k.startswith(prefix + "_") and k not in {f"{prefix}_date", f"{prefix}_status"}})
        pd.DataFrame([data]).to_csv(DASHBOARD_DIR / f"{module}_dashboard.csv", index=False)


def _persist_to_db(snapshot: dict[str, Any], result: Any) -> list[str]:
    from common.database import Database
    db = Database()
    db.connect()
    signal_rows = []
    calc_date = date_cls.fromisoformat(snapshot["date"])
    for module in ["M1", "M2", "M3", "M4", "M5"]:
        module_id = MODULE_IDS[module]
        for key, value in snapshot.items():
            if not key.startswith(module + "_"):
                continue
            name = key[3:]
            if name in {"date", "status"}:
                continue
            is_flag = name.startswith("Flag") or name.endswith("Flag")
            signal_rows.append({
                "signal_date": calc_date,
                "module_id": module_id,
                "signal_name": name,
                "raw_value": None if is_flag else value,
                "mad_score": value if "MAD_score" in name else None,
                "flag": _to_bool(value) if is_flag else False,
                "unit": None,
                "metadata": {"snapshot_status": snapshot.get(f"{module}_status")},
            })
    from repositories import LSIRepository, ModuleSignalsRepository
    signals_repo = ModuleSignalsRepository(db)
    lsi_repo = LSIRepository(db)
    with db.transaction():
        if signal_rows:
            signals_repo.upsert_many_signals(signal_rows)
        lsi_row = lsi_repo.upsert_lsi_value(calc_date, result.lsi, result.status, confidence=result.confidence, model_version=result.model_version)
        if lsi_row.get("id"):
            lsi_repo.upsert_many_module_contributions(lsi_row["id"], result.module_contributions)
    db.close()
    return [c["module_id"] for c in result.module_contributions]


def _run_parsers_safely(force_reload_sources: bool = False) -> list[Any]:
    del force_reload_sources
    try:
        from common.database import Database
        db = Database()
        db.connect()
    except Exception:
        db = None
    try:
        from ingestion.base_parser import BaseParser
        results = BaseParser.run_latest_mode(db=db)
        return results
    except Exception as exc:
        return [{"source_code": "latest_parsers", "status": "failed", "error": str(exc)}]
    finally:
        if db is not None:
            db.close()


def run_latest_recalculation(date: str | None = None, force_reload_sources: bool = False, recalculate_shap: bool = False, regenerate_comment: bool = False) -> LSIResult:
    del recalculate_shap, regenerate_comment
    parser_results = _run_parsers_safely(force_reload_sources=force_reload_sources)
    snapshot = build_latest_snapshot(parser_results=parser_results)
    if date:
        snapshot["date"] = date
    formula_result = calculate_lsi_from_snapshot(snapshot)
    _save_csv_outputs(snapshot, formula_result)
    updated_sources: list[str] = []
    db_warning = None
    try:
        updated_sources = _persist_to_db(snapshot, formula_result)
    except Exception as exc:
        db_warning = f"PostgreSQL persist failed; CSV fallback used: {exc}"
    active_flags = formula_result.active_flags
    if db_warning:
        active_flags = active_flags + [{"module_id": "SYSTEM", "flag_name": "CSV_FALLBACK", "description": db_warning, "severity": 0.2}]
    return LSIResult(
        date=snapshot["date"],
        lsi=formula_result.lsi,
        status=formula_result.status,
        confidence=formula_result.confidence,
        auto_comment="; ".join(formula_result.warnings) if formula_result.warnings else None,
        contributions=formula_result.module_contributions,
        shap_values=[],
        active_flags=active_flags,
        updated_sources=updated_sources,
    )


def main() -> None:
    result = run_latest_recalculation()
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
