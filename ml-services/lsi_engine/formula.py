from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LSIFormulaResult:
    lsi: float
    status: str
    confidence: float
    module_scores: dict[str, float] = field(default_factory=dict)
    module_contributions: list[dict[str, Any]] = field(default_factory=list)
    active_flags: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    model_version: str = "explainable-formula-v1"


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return default if x is None else float(x)
    except Exception:
        return default


def _b(x: Any) -> bool:
    if isinstance(x, str):
        return x.lower() in {"1", "true", "yes", "y"}
    return bool(x)


def stress(mad: Any, cap: float = 6.0) -> float:
    return max(0.0, min(_f(mad), cap))


def inverse_stress(mad: Any, cap: float = 6.0) -> float:
    return max(0.0, min(-_f(mad), cap))


def flag_bonus(flag: Any, value: float = 2.0) -> float:
    return value if _b(flag) else 0.0


def _sigmoid_to_100(x: float) -> float:
    return 100.0 / (1.0 + math.exp(-1.10 * (x - 1.5)))


def _status(lsi: float) -> str:
    if lsi >= 70:
        return "red"
    if lsi >= 40:
        return "yellow"
    return "green"


def calculate_base_lsi(module_scores: dict[str, float]) -> float:
    if not module_scores:
        return 0.0
    return float(sum(module_scores.values()) / len(module_scores))


def calculate_lsi_from_snapshot(snapshot: dict[str, Any]) -> LSIFormulaResult:
    m1 = (
        0.60 * stress(snapshot.get("M1_MAD_score_spread"))
        + 0.30 * stress(snapshot.get("M1_MAD_score_RUONIA"))
        + 0.10 * flag_bonus(snapshot.get("M1_Flag_EndOfPeriod"))
    )
    m2 = (
        0.45 * stress(snapshot.get("M2_MAD_score_cover"))
        + 0.35 * stress(snapshot.get("M2_MAD_score_rate_spread"))
        + 0.10 * stress(snapshot.get("M2_MAD_score_repo_volume"))
        + 0.10 * flag_bonus(snapshot.get("M2_Flag_Demand"))
    )
    # For OFZ cover ratio weak demand is negative MAD: lower cover => higher stress.
    m3 = (
        0.55 * inverse_stress(snapshot.get("M3_MAD_score_cover"))
        + 0.20 * stress(snapshot.get("M3_MAD_score_yield_spread"))
        + 0.15 * flag_bonus(snapshot.get("M3_Flag_Nedospros"))
        - 0.10 * flag_bonus(snapshot.get("M3_Flag_Perespros"), value=1.0)
    )
    # M4 is not an ordinary additive liquidity module. It modifies the base stress by seasonality.
    seasonal = max(0.8, min(_f(snapshot.get("M4_Seasonal_Factor"), 1.0), 1.25))
    m4_flag_score = (
        0.50 * flag_bonus(snapshot.get("M4_Tax_Week_Flag"))
        + 0.25 * flag_bonus(snapshot.get("M4_End_of_Month_Flag"))
        + 0.25 * flag_bonus(snapshot.get("M4_End_of_Quarter_Flag"))
    )
    # For treasury balances/deposits liquidity drain is negative delta/MAD.
    m5 = (
        0.60 * inverse_stress(snapshot.get("M5_MAD_score_CBR"))
        + 0.25 * inverse_stress(snapshot.get("M5_MAD_score_Roskazna"))
        + 0.15 * flag_bonus(snapshot.get("M5_Flag_Budget_Drain"))
    )

    module_scores = {
        "M1": m1,
        "M2": m2,
        "M3": m3,
        "M4": m4_flag_score,
        "M5": m5,
    }
    weights = {"M1": 0.20, "M2": 0.30, "M3": 0.20, "M4": 0.00, "M5": 0.30}
    canonical_module_ids = {
        "M1": "M1_RESERVES",
        "M2": "M2_REPO",
        "M3": "M3_OFZ",
        "M4": "M4_TAX",
        "M5": "M5_TREASURY",
    }
    canonical_module_names = {
        "M1": "M1 reserves / RUONIA",
        "M2": "M2 repo market",
        "M3": "M3 OFZ auctions",
        "M4": "M4 tax seasonality",
        "M5": "M5 treasury liquidity",
    }
    weighted = {k: module_scores[k] * weights[k] for k in weights}
    base_stress = sum(weighted.values())
    adjusted_stress = base_stress * seasonal
    adjusted_stress = adjusted_stress * 1.15
    lsi = round(max(0.0, min(100.0, _sigmoid_to_100(adjusted_stress))), 2)

    # M4 contribution is the marginal seasonal effect in stress-score points.
    contribution_values = dict(weighted)
    contribution_values["M4"] = adjusted_stress - base_stress
    total_abs = sum(abs(v) for v in contribution_values.values()) or 1.0
    contributions = [
        {
            "module_id": canonical_module_ids[k],
            "module_name": canonical_module_names[k],
            "contribution_value": round(v, 4),
            "contribution_percent": round(abs(v) / total_abs * 100.0, 2),
        }
        for k, v in contribution_values.items()
    ]

    flags = []
    flag_specs = [
        ("M1", "Flag_EndOfPeriod", "End of reserve averaging period pressure"),
        ("M2", "Flag_Demand", "Repo demand stress flag"),
        ("M3", "Flag_Nedospros", "Weak OFZ demand flag"),
        ("M3", "Flag_Perespros", "OFZ oversubscription flag"),
        ("M4", "Tax_Week_Flag", "Tax week seasonal liquidity drain"),
        ("M4", "End_of_Month_Flag", "Month-end seasonal liquidity effect"),
        ("M4", "End_of_Quarter_Flag", "Quarter-end seasonal liquidity effect"),
        ("M5", "Flag_Budget_Drain", "Treasury budget-drain flag"),
    ]
    for module, flag, description in flag_specs:
        key = f"{module}_{flag}"
        if _b(snapshot.get(key)):
            severity = min(1.0, max(0.1, module_scores.get(module, 0.0) / 4.0))
            flags.append(
                {
                    "module_id": canonical_module_ids.get(module, module),
                    "flag_name": flag,
                    "description": description,
                    "severity": round(severity, 4),
                }
            )

    missing = [
        m for m in str(snapshot.get("missing_modules", "")).split(",") if m
    ]
    available_modules = 5 - len(missing)
    recency_penalty = 0.0
    confidence = round(
        max(
            0.1,
            min(
                1.0,
                0.2
                + 0.16 * available_modules
                + _f(snapshot.get("snapshot_quality"), 1.0) * 0.2
                - recency_penalty,
            ),
        ),
        2,
    )
    warnings = []
    if missing:
        warnings.append("Missing modules: " + ", ".join(missing))
    raw_warnings = snapshot.get("warnings")
    if raw_warnings:
        warnings.append(str(raw_warnings))
    return LSIFormulaResult(
        lsi=lsi,
        status=_status(lsi),
        confidence=confidence,
        module_scores=module_scores | {"M4_Seasonal_Factor": seasonal},
        module_contributions=contributions,
        active_flags=flags,
        warnings=warnings,
    )
