from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

MODULES = ("M1", "M2", "M3", "M4", "M5")

@dataclass(slots=True)
class ModuleLatestSignals:
    module_id: str
    signal_date: str | None
    signals: dict[str, Any] = field(default_factory=dict)
    status: str = "missing"
    source: str = "fallback"
    warnings: list[str] = field(default_factory=list)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "да"}
    return bool(_safe_float(value, 0.0))


def _find_csv(candidates: list[str]) -> Path | None:
    root = repo_root()
    for pattern in candidates:
        matches = [p for p in root.glob(pattern) if "/dashboard/" not in p.as_posix() and "/snapshots/" not in p.as_posix()]
        matches = sorted(matches, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        if matches:
            return matches[0]
    return None


def _read_latest_csv(path: Path, date_cols: list[str]) -> tuple[pd.Series | None, str | None]:
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None, None
        date_col = next((c for c in date_cols if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col]).sort_values(date_col)
            if df.empty:
                return None, None
            row = df.iloc[-1]
            return row, pd.to_datetime(row[date_col]).date().isoformat()
        return df.iloc[-1], None
    except Exception:
        return None, None


def _missing(module_id: str, warning: str) -> ModuleLatestSignals:
    return ModuleLatestSignals(module_id=module_id, signal_date=None, status="missing", warnings=[warning])


def get_latest_m1_signals() -> ModuleLatestSignals:
    path = _find_csv(["data/processed/**/m1*signal*.csv", "data/processed/**/m1*.csv", "data/raw/**/m1*.csv"])
    if not path:
        return _missing("M1", "M1 CSV fallback not found")
    row, dt = _read_latest_csv(path, ["date", "observation_date", "signal_date"])
    if row is None:
        return _missing("M1", f"M1 CSV is empty or unreadable: {path}")
    return ModuleLatestSignals("M1", dt, {
        "MAD_score_spread": _safe_float(row.get("MAD_score_spread", row.get("normalized_value", row.get("spread_mad", 0.0)))),
        "MAD_score_RUONIA": _safe_float(row.get("MAD_score_RUONIA", row.get("ruonia_mad", 0.0))),
        "Flag_EndOfPeriod": _safe_bool(row.get("Flag_EndOfPeriod", False)),
    }, "fallback", str(path))


def get_latest_m2_signals() -> ModuleLatestSignals:
    path = _find_csv(["data/processed/**/m2*signal*.csv", "data/processed/**/m2*.csv", "data/raw/**/m2*.csv", "data/processed/**/*repo*.csv"])
    if not path:
        return _missing("M2", "M2 CSV fallback not found")
    row, dt = _read_latest_csv(path, ["date", "auction_date", "observation_date", "signal_date"])
    if row is None:
        return _missing("M2", f"M2 CSV is empty or unreadable: {path}")
    return ModuleLatestSignals("M2", dt, {
        "MAD_score_cover": _safe_float(row.get("MAD_score_cover", 0.0)),
        "MAD_score_rate_spread": _safe_float(row.get("MAD_score_rate_spread", row.get("MAD_score_spread", 0.0))),
        "MAD_score_repo_volume": _safe_float(row.get("MAD_score_repo_volume", 0.0)),
        "Flag_Demand": _safe_bool(row.get("Flag_Demand", row.get("demand_flag", False))),
    }, "fallback", str(path))


def get_latest_m3_signals() -> ModuleLatestSignals:
    from modules.m3_ofz.features import build_m3_features
    from modules.m3_ofz.signals import calculate_m3_signals
    path = _find_csv(["data/processed/**/m3*signal*.csv", "data/processed/**/ofz*signal*.csv", "data/processed/**/ofz_auction_results.csv", "data/raw/**/*ofz*.csv"])
    if not path:
        return _missing("M3", "M3 OFZ CSV fallback not found")
    try:
        df = pd.read_csv(path)
        if "MAD_score_cover" not in df.columns and "cover_ratio" in df.columns:
            df = calculate_m3_signals(build_m3_features(df))
        date_col = "auction_date" if "auction_date" in df.columns else "date"
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).sort_values(date_col)
        row = df.iloc[-1]
        return ModuleLatestSignals("M3", pd.to_datetime(row[date_col]).date().isoformat(), {
            "MAD_score_cover": _safe_float(row.get("MAD_score_cover", 0.0)),
            "MAD_score_yield_spread": _safe_float(row.get("MAD_score_yield_spread", 0.0)),
            "Flag_Nedospros": _safe_bool(row.get("Flag_Nedospros", False)),
            "Flag_Perespros": _safe_bool(row.get("Flag_Perespros", False)),
        }, "fallback", str(path))
    except Exception as exc:
        return _missing("M3", f"M3 CSV fallback failed: {exc}")


def get_latest_m4_signals() -> ModuleLatestSignals:
    path = _find_csv(["data/processed/**/m4*signal*.csv", "data/processed/**/*tax*.csv", "data/raw/**/*tax*.csv"])
    if not path:
        today = date.today()
        return ModuleLatestSignals("M4", today.isoformat(), {
            "Tax_Week_Flag": False,
            "End_of_Month_Flag": today.day >= 25,
            "End_of_Quarter_Flag": today.month in (3, 6, 9, 12) and today.day >= 20,
            "Seasonal_Factor": 1.0,
        }, "fallback", "calendar_fallback", ["M4 tax calendar CSV not found; used neutral calendar fallback"])
    row, dt = _read_latest_csv(path, ["date", "observation_date", "tax_date"])
    if row is None:
        return _missing("M4", f"M4 CSV is empty or unreadable: {path}")
    return ModuleLatestSignals("M4", dt, {
        "Tax_Week_Flag": _safe_bool(row.get("Tax_Week_Flag", row.get("tax_week_flag", False))),
        "End_of_Month_Flag": _safe_bool(row.get("End_of_Month_Flag", False)),
        "End_of_Quarter_Flag": _safe_bool(row.get("End_of_Quarter_Flag", False)),
        "Seasonal_Factor": _safe_float(row.get("Seasonal_Factor", 1.0), 1.0),
    }, "fallback", str(path))


def get_latest_m5_signals() -> ModuleLatestSignals:
    from modules.m5_treasury.features import build_m5_features
    from modules.m5_treasury.signals import calculate_m5_signals
    path = _find_csv(["data/processed/**/m5*signal*.csv", "data/processed/**/m5*feature*.csv", "data/raw/**/m5*feature*.csv", "data/raw/**/*treasury*.csv"])
    if not path:
        return _missing("M5", "M5 treasury CSV fallback not found")
    try:
        df = pd.read_csv(path)
        if "MAD_score_CBR" not in df.columns:
            if "observation_date" in df.columns:
                df = calculate_m5_signals(build_m5_features(df))
            else:
                df = calculate_m5_signals(df)
        date_col = "date" if "date" in df.columns else "observation_date"
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).sort_values(date_col)
        row = df.iloc[-1]
        return ModuleLatestSignals("M5", pd.to_datetime(row[date_col]).date().isoformat(), {
            "MAD_score_CBR": _safe_float(row.get("MAD_score_CBR", 0.0)),
            "MAD_score_Roskazna": _safe_float(row.get("MAD_score_Roskazna", 0.0)),
            "Flag_Budget_Drain": _safe_bool(row.get("Flag_Budget_Drain", False)),
        }, "fallback", str(path))
    except Exception as exc:
        return _missing("M5", f"M5 CSV fallback failed: {exc}")


def build_latest_snapshot(parser_results: list[Any] | None = None) -> dict[str, Any]:
    modules = [get_latest_m1_signals(), get_latest_m2_signals(), get_latest_m3_signals(), get_latest_m4_signals(), get_latest_m5_signals()]
    now = datetime.now(timezone.utc)
    snapshot: dict[str, Any] = {"date": date.today().isoformat(), "calculated_at": now.isoformat()}
    missing: list[str] = []
    warnings: list[str] = []
    for m in modules:
        if m.status in {"missing", "failed"}:
            missing.append(m.module_id)
        warnings.extend([f"{m.module_id}: {w}" for w in m.warnings])
        snapshot[f"{m.module_id}_date"] = m.signal_date
        snapshot[f"{m.module_id}_status"] = m.status
        for key, value in m.signals.items():
            snapshot[f"{m.module_id}_{key}"] = value
    defaults = {
        "M1_MAD_score_spread": 0.0, "M1_MAD_score_RUONIA": 0.0, "M1_Flag_EndOfPeriod": False,
        "M2_MAD_score_cover": 0.0, "M2_MAD_score_rate_spread": 0.0, "M2_MAD_score_repo_volume": 0.0, "M2_Flag_Demand": False,
        "M3_MAD_score_cover": 0.0, "M3_MAD_score_yield_spread": 0.0, "M3_Flag_Nedospros": False, "M3_Flag_Perespros": False,
        "M4_Tax_Week_Flag": False, "M4_End_of_Month_Flag": False, "M4_End_of_Quarter_Flag": False, "M4_Seasonal_Factor": 1.0,
        "M5_MAD_score_CBR": 0.0, "M5_MAD_score_Roskazna": 0.0, "M5_Flag_Budget_Drain": False,
    }
    for key, value in defaults.items():
        snapshot.setdefault(key, value)
    snapshot["missing_modules"] = ",".join(missing)
    snapshot["snapshot_quality"] = max(0.0, 1.0 - 0.15 * len(missing))
    snapshot["warnings"] = json.dumps(warnings, ensure_ascii=False)
    snapshot["source_summary"] = json.dumps([getattr(r, "__dict__", str(r)) for r in parser_results or []], ensure_ascii=False, default=str)
    return snapshot
