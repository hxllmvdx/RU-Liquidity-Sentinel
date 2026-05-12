from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from explainability.shap_explainer import calculate_formula_shap
from lsi_engine.formula import calculate_lsi_from_snapshot
from pipeline.build_wide_dataset import build_wide_lsi_dataset, repo_root

logger = logging.getLogger(__name__)

DASHBOARD_DIR = repo_root() / "data" / "processed" / "dashboard"
WIDE_PATH = repo_root() / "data" / "processed" / "lsi" / "lsi_wide_daily_dataset.csv"
MODULE_IDS = {"M1": "M1_RESERVES", "M2": "M2_REPO", "M3": "M3_OFZ", "M4": "M4_TAX", "M5": "M5_TREASURY"}


def _boolish(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "да"}
    return bool(value)


def _normalize_snapshot(row: pd.Series) -> dict[str, Any]:
    snapshot = row.to_dict()
    snapshot["date"] = str(snapshot["date"])[:10]
    for key in list(snapshot):
        if "Flag" in key:
            snapshot[key] = _boolish(snapshot[key])
    snapshot.setdefault("M4_Seasonal_Factor", 1.0)
    snapshot.setdefault("missing_modules", "")
    snapshot.setdefault("snapshot_quality", 1.0)
    return snapshot


def calculate_lsi_history_from_wide_dataset(wide_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, wide_row in wide_df.sort_values("date").iterrows():
        snapshot = _normalize_snapshot(wide_row)
        result = calculate_lsi_from_snapshot(snapshot)
        rows.append({
            "date": snapshot["date"],
            "LSI": result.lsi,
            "status": result.status,
            "confidence": result.confidence,
            "M1_score": result.module_scores.get("M1", 0.0),
            "M2_score": result.module_scores.get("M2", 0.0),
            "M3_score": result.module_scores.get("M3", 0.0),
            "M4_Seasonal_Factor": result.module_scores.get("M4_Seasonal_Factor", 1.0),
            "M5_score": result.module_scores.get("M5", 0.0),
            "M1_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M1_RESERVES"), 0.0),
            "M2_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M2_REPO"), 0.0),
            "M3_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M3_OFZ"), 0.0),
            "M4_effect": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M4_TAX"), 0.0),
            "M5_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] == "M5_TREASURY"), 0.0),
            "active_flags_count": len(result.active_flags),
            "model_version": result.model_version,
            "missing_modules": snapshot.get("missing_modules", ""),
        })
    return pd.DataFrame(rows)


def _signal_rows_for_snapshot(snapshot: dict[str, Any], calc_date: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module in ["M1", "M2", "M3", "M4", "M5"]:
        module_id = MODULE_IDS[module]
        for key, value in snapshot.items():
            if not key.startswith(module + "_"):
                continue
            name = key[3:]
            if name in {"date", "status"}:
                continue
            is_flag = name.startswith("Flag") or name.endswith("Flag")
            rows.append({
                "signal_date": calc_date,
                "module_id": module_id,
                "signal_name": name,
                "raw_value": None if is_flag else (float(value) if pd.notna(value) and str(value) != "" else None),
                "mad_score": float(value) if "MAD_score" in name and pd.notna(value) and str(value) != "" else None,
                "flag": _boolish(value) if is_flag else False,
                "unit": None,
                "metadata": {"snapshot_status": snapshot.get(f"{module}_status"), "source_summary": snapshot.get("source_summary")},
            })
    return rows


def save_lsi_history_dashboard(history: pd.DataFrame) -> Path:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    path = DASHBOARD_DIR / "lsi_dashboard.csv"
    history = history.drop_duplicates(subset=["date"], keep="last").sort_values("date")
    history.to_csv(path, index=False)
    return path


def persist_lsi_history(wide_df: pd.DataFrame, history_df: pd.DataFrame) -> int:
    from common.database import Database
    from repositories import LSIRepository, ModuleSignalsRepository, ShapRepository

    db = Database()
    db.connect()
    persisted = 0
    try:
        lsi_repo = LSIRepository(db)
        signals_repo = ModuleSignalsRepository(db)
        shap_repo = ShapRepository(db)
        with db.transaction():
            for _, wide_row in wide_df.sort_values("date").iterrows():
                snapshot = _normalize_snapshot(wide_row)
                calc_date = datetime.strptime(snapshot["date"], "%Y-%m-%d").date()
                result = calculate_lsi_from_snapshot(snapshot)
                lsi_row = lsi_repo.upsert_lsi_value(
                    calculation_date=calc_date,
                    lsi=result.lsi,
                    status=result.status,
                    confidence=result.confidence,
                    auto_comment=None,
                    model_version=result.model_version,
                )
                signals_repo.upsert_many_signals(_signal_rows_for_snapshot(snapshot, calc_date))
                signals_repo.clear_active_flags_for_date(calc_date)
                if result.active_flags:
                    signals_repo.upsert_many_active_flags([
                        {
                            "flag_date": calc_date,
                            "module_id": item["module_id"],
                            "flag_name": item["flag_name"],
                            "description": item.get("description"),
                            "severity": item.get("severity"),
                        }
                        for item in result.active_flags
                    ])
                if lsi_row.get("id"):
                    lsi_repo.upsert_many_module_contributions(lsi_row["id"], result.module_contributions)
                    shap_repo.delete_shap_values_for_lsi(lsi_row["id"])
                    shap_values = calculate_formula_shap(snapshot)
                    if shap_values:
                        shap_repo.upsert_many_shap_values(lsi_row["id"], shap_values)
                persisted += 1
    finally:
        db.close()
    return persisted


def build_and_persist_lsi_history(persist: bool = True) -> dict[str, Any]:
    wide_df = build_wide_lsi_dataset()
    history_df = calculate_lsi_history_from_wide_dataset(wide_df)
    dashboard_path = save_lsi_history_dashboard(history_df)
    persisted_rows = persist_lsi_history(wide_df, history_df) if persist else 0
    return {
        "rows": int(len(history_df)),
        "persisted": int(persisted_rows),
        "wide_dataset_rows": int(len(wide_df)),
        "dashboard_path": str(dashboard_path),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(json.dumps(build_and_persist_lsi_history(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
