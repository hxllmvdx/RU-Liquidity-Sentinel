from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path

import pandas as pd

from common.database import Database
from common.db_models import LSIResult
from explainability.shap_explainer import explain_with_shap
from ingestion.base_parser import BaseParser
from llm.auto_comment import generate_auto_comment
from lsi_engine.formula import calculate_base_lsi
from lsi_engine.status import resolve_status
from modules.m3_ofz.features import build_m3_features
from modules.m3_ofz.signals import calculate_m3_signals
from modules.m5_treasury.features import build_m5_features
from modules.m5_treasury.signals import calculate_m5_signals
from repositories import LSIRepository, ModuleSignalsRepository, RagRepository, ShapRepository


def _load_m3_signals() -> pd.DataFrame:
    path = Path(__file__).resolve().parents[2] / "data" / "processed" / "ofz_auction_results.csv"
    if not path.exists():
        return pd.DataFrame()
    return calculate_m3_signals(build_m3_features(pd.read_csv(path)))


def _load_m5_signals() -> pd.DataFrame:
    path = Path(__file__).resolve().parents[2] / "data" / "raw" / "treasury" / "m5_treasury" / "m5_treasury_features_2021-01-01_2026-05-10.csv"
    if not path.exists():
        return pd.DataFrame()
    return calculate_m5_signals(build_m5_features(pd.read_csv(path)))


def _extract_signal_rows(calculation_date: date_cls, m3_df: pd.DataFrame, m5_df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    signal_rows: list[dict] = []
    active_flags: list[dict] = []

    if not m3_df.empty:
        latest_m3_date = pd.to_datetime(m3_df["auction_date"]).dt.date.max()
        latest_m3 = m3_df[pd.to_datetime(m3_df["auction_date"]).dt.date == latest_m3_date]
        for _, row in latest_m3.iterrows():
            signal_rows.extend([
                {"signal_date": calculation_date, "module_id": "M3_OFZ", "signal_name": "MAD_score_cover", "raw_value": row.get("cover_ratio"), "mad_score": row.get("MAD_score_cover"), "flag": bool(row.get("Stress_Flag")), "unit": "ratio", "metadata": {"ofz_issue": row.get("ofz_issue"), "stress_level": str(row.get("Stress_Level"))}},
                {"signal_date": calculation_date, "module_id": "M3_OFZ", "signal_name": "MAD_score_yield_spread", "raw_value": row.get("yield_spread"), "mad_score": row.get("MAD_score_yield_spread"), "flag": False, "unit": "bp", "metadata": {"ofz_issue": row.get("ofz_issue")}},
                {"signal_date": calculation_date, "module_id": "M3_OFZ", "signal_name": "Stress_Score", "raw_value": row.get("Stress_Score"), "mad_score": None, "flag": bool(row.get("Stress_Flag")), "unit": "score", "metadata": {"ofz_issue": row.get("ofz_issue")}},
            ])
            if int(row.get("Flag_Nedospros", 0)) == 1:
                active_flags.append({"flag_date": calculation_date, "module_id": "M3_OFZ", "flag_name": "Flag_Nedospros", "description": "Cover ratio below 1.2", "severity": 0.8})
            if int(row.get("Flag_Perespros", 0)) == 1:
                active_flags.append({"flag_date": calculation_date, "module_id": "M3_OFZ", "flag_name": "Flag_Perespros", "description": "Cover ratio above 2.0", "severity": 0.3})

    if not m5_df.empty:
        latest_m5_date = pd.to_datetime(m5_df["date"]).dt.date.max()
        latest_m5 = m5_df[pd.to_datetime(m5_df["date"]).dt.date == latest_m5_date]
        for _, row in latest_m5.iterrows():
            signal_rows.extend([
                {"signal_date": calculation_date, "module_id": "M5_TREASURY", "signal_name": "MAD_score_CBR", "raw_value": row.get("cbr_weekly_delta_bln_rub"), "mad_score": row.get("MAD_score_CBR"), "flag": bool(row.get("Flag_Budget_Drain")), "unit": "bln_rub", "metadata": {"state": row.get("Budget_Drain_State")}},
                {"signal_date": calculation_date, "module_id": "M5_TREASURY", "signal_name": "MAD_score_Roskazna", "raw_value": row.get("roskazna_weekly_delta_bln_rub"), "mad_score": row.get("MAD_score_Roskazna"), "flag": bool(row.get("Flag_Budget_Drain")), "unit": "bln_rub", "metadata": {"state": row.get("Budget_Drain_State")}},
                {"signal_date": calculation_date, "module_id": "M5_TREASURY", "signal_name": "Budget_Drain_Score", "raw_value": row.get("Budget_Drain_Score"), "mad_score": None, "flag": bool(row.get("Flag_Budget_Drain")), "unit": "score", "metadata": {"state": row.get("Budget_Drain_State")}},
            ])
            if int(row.get("Flag_Budget_Drain", 0)) == 1:
                active_flags.append({"flag_date": calculation_date, "module_id": "M5_TREASURY", "flag_name": "Flag_Budget_Drain", "description": str(row.get("Budget_Drain_State")), "severity": float(min(row.get("Budget_Drain_Score", 0.0), 1.0))})

    return signal_rows, active_flags


def run_latest_recalculation(date: str | None = None, force_reload_sources: bool = False, recalculate_shap: bool = True, regenerate_comment: bool = True) -> LSIResult:
    del force_reload_sources
    calculation_date = date_cls.fromisoformat(date) if date else date_cls.today()
    db = Database()
    db.connect()
    signals_repo = ModuleSignalsRepository(db)
    lsi_repo = LSIRepository(db)
    shap_repo = ShapRepository(db)
    rag_repo = RagRepository(db)

    parser_results = BaseParser.run_latest_mode(db=db)
    updated_sources = [item.source_code for item in parser_results if item.status in ("success", "partial", "stale")]

    m3_df = _load_m3_signals()
    m5_df = _load_m5_signals()
    signal_rows, active_flags = _extract_signal_rows(calculation_date, m3_df, m5_df)

    signals_repo.clear_active_flags_for_date(calculation_date)
    if signal_rows:
        signals_repo.upsert_many_signals(signal_rows)
    if active_flags:
        signals_repo.upsert_many_active_flags(active_flags)

    latest_signals = signals_repo.get_latest_signals()
    module_scores: dict[str, float] = {}
    for signal in latest_signals:
        signal_name = signal["signal_name"]
        if signal_name == "Stress_Score" and signal.get("raw_value") is not None:
            module_scores["m3_ofz"] = max(module_scores.get("m3_ofz", 0.0), float(signal["raw_value"]) * 100.0)
        if signal_name == "Budget_Drain_Score" and signal.get("raw_value") is not None:
            module_scores["m5_treasury"] = max(module_scores.get("m5_treasury", 0.0), float(signal["raw_value"]) * 100.0)

    lsi_value = round(calculate_base_lsi(module_scores), 2) if module_scores else 0.0
    status = resolve_status(lsi_value)
    lsi_row = lsi_repo.upsert_lsi_value(calculation_date, lsi_value, status, confidence=0.5, model_version="latest-recalc-v2")

    total = sum(module_scores.values()) or 1.0
    contributions = [
        {"module_id": key.upper(), "module_name": key.upper(), "contribution_value": value, "contribution_percent": round(value / total * 100.0, 2)}
        for key, value in module_scores.items()
    ]
    if contributions:
        lsi_repo.upsert_many_module_contributions(lsi_row["id"], contributions)

    shap_values = []
    if recalculate_shap:
        shap_payload = explain_with_shap(signal_rows)
        shap_values = shap_payload.get("top_features", []) if isinstance(shap_payload, dict) else []
        if shap_values:
            shap_repo.delete_shap_values_for_lsi(lsi_row["id"])
            shap_repo.upsert_many_shap_values(lsi_row["id"], shap_values)

    comment = None
    if regenerate_comment:
        comment = generate_auto_comment({"date": calculation_date.isoformat(), "lsi": lsi_value, "status": status, "updated_sources": updated_sources, "active_flags": active_flags})
        lsi_repo.update_auto_comment(calculation_date, comment)

    rag_repo.delete_documents_by_source("latest_recalculation", calculation_date.isoformat())
    rag_repo.upsert_document(
        source_type="latest_recalculation",
        source_id=calculation_date.isoformat(),
        title=f"LSI summary for {calculation_date.isoformat()}",
        content=f"LSI={lsi_value}; status={status}; sources={', '.join(updated_sources)}",
        metadata={"contributions": contributions, "active_flags": active_flags},
    )

    db.close()
    return LSIResult(
        date=calculation_date.isoformat(),
        lsi=lsi_value,
        status=status,
        confidence=0.5,
        auto_comment=comment,
        contributions=contributions,
        shap_values=shap_values,
        active_flags=active_flags,
        updated_sources=updated_sources,
    )
