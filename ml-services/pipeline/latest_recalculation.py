from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import pandas as pd

from common.db_models import LSIResult
from lsi_engine.formula import calculate_lsi_from_snapshot
from explainability.shap_explainer import calculate_formula_shap
from pipeline.build_wide_dataset import build_wide_lsi_dataset, repo_root
from pipeline.lsi_history import build_and_persist_lsi_history
from rag.lsi_rag_indexer import rebuild_lsi_rag_index

logger = logging.getLogger(__name__)

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
        "M1_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] in {"M1", "M1_RESERVES"}), 0.0),
        "M2_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] in {"M2", "M2_REPO"}), 0.0),
        "M3_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] in {"M3", "M3_OFZ"}), 0.0),
        "M4_effect": result.module_scores.get("M4_Seasonal_Factor", 1.0),
        "M5_contribution": next((c["contribution_value"] for c in result.module_contributions if c["module_id"] in {"M5", "M5_TREASURY"}), 0.0),
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


def _persist_to_db(snapshot: dict[str, Any], result: Any, auto_comment: str | None = None, shap_values: list[dict[str, Any]] | None = None) -> list[str]:
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
    from repositories import LSIRepository, ModuleSignalsRepository, ShapRepository
    signals_repo = ModuleSignalsRepository(db)
    lsi_repo = LSIRepository(db)
    shap_repo = ShapRepository(db)
    with db.transaction():
        if signal_rows:
            signals_repo.upsert_many_signals(signal_rows)
        lsi_row = lsi_repo.upsert_lsi_value(calc_date, result.lsi, result.status, confidence=result.confidence, auto_comment=auto_comment, model_version=result.model_version)
        if lsi_row.get("id"):
            lsi_repo.upsert_many_module_contributions(lsi_row["id"], result.module_contributions)
            shap_repo.delete_shap_values_for_lsi(lsi_row["id"])
            if shap_values:
                shap_repo.upsert_many_shap_values(lsi_row["id"], shap_values)
        signals_repo.clear_active_flags_for_date(calc_date)
        active_flag_rows = []
        for flag in result.active_flags:
            module_id = flag.get("module_id")
            if module_id not in set(MODULE_IDS.values()):
                continue
            active_flag_rows.append({
                "flag_date": calc_date,
                "module_id": module_id,
                "flag_name": str(flag.get("flag_name", "")),
                "description": str(flag.get("description", "")),
                "severity": float(flag.get("severity", 0.5)),
            })
        if active_flag_rows:
            signals_repo.upsert_many_active_flags(active_flag_rows)
    db.close()
    return [c["module_id"] for c in result.module_contributions]



def _try_backfill_lsi_history() -> dict[str, Any] | None:
    try:
        result = build_and_persist_lsi_history(persist=True)
        if result.get("rows", 0):
            logger.info("LSI history backfill completed: %s", result)
        return result
    except Exception as exc:
        logger.warning("LSI history backfill failed: %s", exc, exc_info=True)
        return {"error": str(exc)}


def _build_auto_comment(snapshot: dict[str, Any], result: Any, history_df: pd.DataFrame | None = None) -> str:
    flags = ", ".join(f"{f.get('module_id')}:{f.get('flag_name')}" for f in result.active_flags) or "нет активных флагов"
    missing = snapshot.get("missing_modules") or "нет"
    trend = "недостаточно истории"
    if history_df is not None and not history_df.empty:
        tail = history_df.sort_values("date").tail(7)
        if len(tail) >= 2:
            delta = float(tail["LSI"].iloc[-1] - tail["LSI"].iloc[0])
            trend = f"изменение за 7 дней {delta:+.2f} п."
    top_contribs = ", ".join(
        f"{c.get('module_name')}={float(c.get('contribution_value', 0.0)):.2f}"
        for c in sorted(result.module_contributions, key=lambda x: abs(float(x.get("contribution_value", 0.0))), reverse=True)[:3]
    ) or "нет"
    base = (
        f"Текущий LSI={result.lsi:.2f}, статус={result.status}, confidence={result.confidence:.2f}. "
        f"Тренд: {trend}. Топ вкладов: {top_contribs}. Активные флаги: {flags}. "
        f"Отсутствующие модули: {missing}."
    )
    try:
        from llm.client import LLMClient
        prompt = (
            "Ты аналитик RU Liquidity Sentinel. Дай короткий комментарий для главного dashboard на русском. "
            "Используй только эти данные, не выдумывай факты. "
            f"Данные: {base}"
        )
        return (LLMClient().generate(prompt) or "").strip()[:1200] or base
    except Exception as exc:
        logger.warning("LLM auto comment failed, deterministic comment used: %s", exc)
        zone = {"green": "зелёной", "yellow": "жёлтой", "red": "красной"}.get(result.status, result.status)
        return f"LSI находится в {zone} зоне. Confidence снижена из-за отсутствующих модулей: {missing}."

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
    history_backfill = _try_backfill_lsi_history()
    parser_results = _run_parsers_safely(force_reload_sources=force_reload_sources)
    wide_df = build_wide_lsi_dataset()
    if wide_df.empty:
        raise RuntimeError("wide LSI dataset is empty after latest parsers")
    snapshot = wide_df.sort_values("date").iloc[-1].to_dict()
    snapshot["date"] = str(snapshot["date"])[:10]
    snapshot["source_summary"] = json.dumps([getattr(r, "__dict__", str(r)) for r in parser_results or []], ensure_ascii=False, default=str)
    if date:
        snapshot["date"] = date
    formula_result = calculate_lsi_from_snapshot(snapshot)
    shap_values = calculate_formula_shap(snapshot, limit=20)
    _save_csv_outputs(snapshot, formula_result)
    history_df = pd.read_csv(DASHBOARD_DIR / "lsi_dashboard.csv") if (DASHBOARD_DIR / "lsi_dashboard.csv").exists() else None
    auto_comment = _build_auto_comment(snapshot, formula_result, history_df)
    updated_sources: list[str] = []
    db_warning = None
    try:
        updated_sources = _persist_to_db(snapshot, formula_result, auto_comment=auto_comment, shap_values=shap_values)
        rebuild_lsi_rag_index(limit_days=30)
    except Exception as exc:
        db_warning = f"PostgreSQL persist failed; CSV fallback used: {exc}"
        logger.warning(db_warning, exc_info=True)
    active_flags = formula_result.active_flags
    if db_warning:
        logger.warning("Recalculation completed without PostgreSQL persistence: %s", db_warning)
    return LSIResult(
        date=snapshot["date"],
        lsi=formula_result.lsi,
        status=formula_result.status,
        confidence=formula_result.confidence,
        auto_comment=auto_comment,
        contributions=formula_result.module_contributions,
        shap_values=shap_values,
        active_flags=active_flags,
        updated_sources=updated_sources,
    )


def main() -> None:
    result = run_latest_recalculation()
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
