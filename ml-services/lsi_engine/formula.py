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
    return 100.0 / (1.0 + math.exp(-0.9 * (x - 2.0)))


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
    m1 = 0.60 * stress(snapshot.get("M1_MAD_score_spread")) + 0.30 * stress(snapshot.get("M1_MAD_score_RUONIA")) + 0.10 * flag_bonus(snapshot.get("M1_Flag_EndOfPeriod"))
    m2 = 0.55 * stress(snapshot.get("M2_MAD_score_cover")) + 0.35 * stress(snapshot.get("M2_MAD_score_rate_spread")) + 0.10 * flag_bonus(snapshot.get("M2_Flag_Demand"))
    # For OFZ cover ratio weak demand is negative MAD: lower cover => higher stress.
    m3 = 0.60 * inverse_stress(snapshot.get("M3_MAD_score_cover")) + 0.25 * stress(snapshot.get("M3_MAD_score_yield_spread")) + 0.15 * flag_bonus(snapshot.get("M3_Flag_Nedospros"))
    # For treasury balances/deposits liquidity drain is negative delta/MAD.
    m5 = 0.60 * inverse_stress(snapshot.get("M5_MAD_score_CBR")) + 0.25 * inverse_stress(snapshot.get("M5_MAD_score_Roskazna")) + 0.15 * flag_bonus(snapshot.get("M5_Flag_Budget_Drain"))
    seasonal = max(0.5, min(_f(snapshot.get("M4_Seasonal_Factor"), 1.0), 1.5))
    module_scores = {"M1": m1, "M2": m2, "M3": m3, "M5": m5}
    weights = {"M1": 0.20, "M2": 0.30, "M3": 0.20, "M5": 0.30}
    weighted = {k: module_scores[k] * weights[k] for k in module_scores}
    base_stress = sum(weighted.values())
    adjusted_stress = base_stress * seasonal
    lsi = round(max(0.0, min(100.0, _sigmoid_to_100(adjusted_stress))), 2)
    total = sum(weighted.values()) or 1.0
    contributions = [
        {"module_id": k, "module_name": k, "contribution_value": round(v, 4), "contribution_percent": round(v / total * 100.0, 2)}
        for k, v in weighted.items()
    ]
    flags = []
    for module, flag in [("M1", "Flag_EndOfPeriod"), ("M2", "Flag_Demand"), ("M3", "Flag_Nedospros"), ("M3", "Flag_Perespros"), ("M5", "Flag_Budget_Drain")]:
        key = f"{module}_{flag}"
        if _b(snapshot.get(key)):
            flags.append({"module_id": module, "flag_name": flag, "description": key, "severity": 0.5})
    missing = [m for m in str(snapshot.get("missing_modules", "")).split(",") if m]
    confidence = round(max(0.1, min(1.0, _f(snapshot.get("snapshot_quality"), 1.0) - 0.08 * len(missing))), 2)
    warnings = []
    if missing:
        warnings.append("Missing modules: " + ", ".join(missing))
    raw_warnings = snapshot.get("warnings")
    if raw_warnings:
        warnings.append(str(raw_warnings))
    return LSIFormulaResult(lsi=lsi, status=_status(lsi), confidence=confidence, module_scores=module_scores | {"M4_Seasonal_Factor": seasonal}, module_contributions=contributions, active_flags=flags, warnings=warnings)
