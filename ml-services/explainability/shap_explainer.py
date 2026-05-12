from __future__ import annotations

from typing import Any

FEATURE_MODULES = {
    "M1_MAD_score_spread": "M1_RESERVES",
    "M1_MAD_score_RUONIA": "M1_RESERVES",
    "M1_Flag_EndOfPeriod": "M1_RESERVES",
    "M2_MAD_score_cover": "M2_REPO",
    "M2_MAD_score_rate_spread": "M2_REPO",
    "M2_MAD_score_repo_volume": "M2_REPO",
    "M2_Flag_Demand": "M2_REPO",
    "M3_MAD_score_cover": "M3_OFZ",
    "M3_MAD_score_yield_spread": "M3_OFZ",
    "M3_Flag_Nedospros": "M3_OFZ",
    "M3_Flag_Perespros": "M3_OFZ",
    "M4_Tax_Week_Flag": "M4_TAX",
    "M4_End_of_Month_Flag": "M4_TAX",
    "M4_End_of_Quarter_Flag": "M4_TAX",
    "M4_Seasonal_Factor": "M4_TAX",
    "M5_MAD_score_CBR": "M5_TREASURY",
    "M5_MAD_score_Roskazna": "M5_TREASURY",
    "M5_Flag_Budget_Drain": "M5_TREASURY",
}

BASELINE_VALUES = {
    "M4_Seasonal_Factor": 1.0,
}


def _baseline_for(feature_name: str, value: Any) -> Any:
    if feature_name in BASELINE_VALUES:
        return BASELINE_VALUES[feature_name]
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "false", "1", "0", "yes", "no"}:
            return False
    return 0.0


def calculate_formula_shap(snapshot: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
    """Return deterministic SHAP-like local attributions for the formula LSI.

    This is not a TreeSHAP explainer: current LSI is formula-based, not tree-based.
    The value is the leave-one-feature-out delta in LSI points versus a neutral
    baseline for this feature. It is stable, auditable and tied to the real
    calculation input used by `calculate_lsi_from_snapshot`.
    """
    from lsi_engine.formula import calculate_lsi_from_snapshot

    try:
        full_lsi = calculate_lsi_from_snapshot(snapshot).lsi
        rows: list[dict[str, Any]] = []
        for feature_name, module_id in FEATURE_MODULES.items():
            if feature_name not in snapshot:
                continue
            neutral_snapshot = dict(snapshot)
            neutral_snapshot[feature_name] = _baseline_for(feature_name, snapshot.get(feature_name))
            neutral_lsi = calculate_lsi_from_snapshot(neutral_snapshot).lsi
            value = round(full_lsi - neutral_lsi, 4)
            if abs(value) < 1e-9:
                continue
            rows.append({
                "feature_name": feature_name,
                "module_id": module_id,
                "value": value,
                "abs_value": round(abs(value), 4),
            })
        rows.sort(key=lambda item: (item["abs_value"], item["feature_name"]), reverse=True)
        return rows[:limit] if limit else rows
    except Exception:
        return []


def formula_shap_values(snapshot: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
    return calculate_formula_shap(snapshot, limit=limit)
