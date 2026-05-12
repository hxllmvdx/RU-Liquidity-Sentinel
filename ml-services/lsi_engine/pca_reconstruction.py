from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import RobustScaler


MODEL_VERSION = "pca-reconstruction-error-v1"
DEFAULT_N_COMPONENTS = 6
DEFAULT_ERROR_QUANTILE = 0.99

MODULE_FEATURES: dict[str, list[str]] = {
    "M1": ["mad_score_ruonia", "mad_score_spread", "flag_end_period"],
    "M2": ["MAD_score_rate_spread", "MAD_score_cover", "Flag_Demand", "MAD_score_repo_volume"],
    "M3": ["MAD_score_yield_spread", "Flag_Nedospros", "Flag_PeresprosMAD_score_CBR", "MAD_score_cover_m3"],
    "M4": ["Tax_Week_Flag", "End_of_Month_Flag", "End_of_Quarter_Flag", "Seasonal_Factor"],
    "M5": ["MAD_score_Roskazna", "Flag_Budget_Drain", "Flag_Treasury_Placement_Drop"],
}

FLAG_COLUMNS = {
    "flag_end_period",
    "Flag_Demand",
    "Tax_Week_Flag",
    "End_of_Month_Flag",
    "End_of_Quarter_Flag",
    "Flag_Nedospros",
    "Flag_PeresprosMAD_score_CBR",
    "Flag_Budget_Drain",
    "Flag_Treasury_Placement_Drop",
}


@dataclass(slots=True)
class PCALSIResult:
    date: str
    lsi: float
    status: str
    confidence: float
    module_scores: dict[str, float] = field(default_factory=dict)
    module_contributions: dict[str, float] = field(default_factory=dict)
    active_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    model_version: str = MODEL_VERSION


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_dataset_path() -> Path:
    candidates = [
        _repo_root() / "data" / "processed" / "all_newdf.csv",
        _repo_root().parent / "all_newdf.csv",
        Path("/mnt/data/all_newdf.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _coerce_numeric_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    for col in frame.columns:
        if col.lower() in {"date", "calculation_date", "calculated_at"}:
            continue
        if frame[col].dtype == bool:
            frame[col] = frame[col].astype(int)
        else:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def load_pca_dataset(path: str | Path | None = None) -> pd.DataFrame:
    dataset_path = Path(path) if path is not None else default_dataset_path()
    if not dataset_path.exists():
        raise FileNotFoundError(f"PCA dataset not found: {dataset_path}")
    frame = pd.read_csv(dataset_path)
    frame = _coerce_numeric_frame(frame)
    # Keep rows that have at least one actual signal. Fill remaining gaps with neutral zeroes for MVP.
    numeric_cols = [c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c])]
    if not numeric_cols:
        raise ValueError(f"PCA dataset has no numeric columns: {dataset_path}")
    frame = frame.dropna(how="all", subset=numeric_cols).reset_index(drop=True)
    return frame.fillna(0.0)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    excluded = {"date", "calculation_date", "calculated_at"}
    cols = [
        col for col in df.columns
        if col not in excluded and col != "Unnamed: 0" and pd.api.types.is_numeric_dtype(df[col])
    ]
    if not cols:
        raise ValueError("No numeric feature columns available for PCA")
    return cols


def _fit_reconstruct(df: pd.DataFrame, feature_cols: list[str], n_components: int = DEFAULT_N_COMPONENTS) -> tuple[np.ndarray, np.ndarray, np.ndarray, RobustScaler, PCA]:
    x = df[feature_cols].astype(float).to_numpy()
    scaler = RobustScaler()
    x_scaled = scaler.fit_transform(x)
    n_components = max(1, min(n_components, x_scaled.shape[1], x_scaled.shape[0] - 1))
    pca = PCA(n_components=n_components, random_state=42)
    z = pca.fit_transform(x_scaled)
    x_reconstructed = pca.inverse_transform(z)
    feature_errors = (x_scaled - x_reconstructed) ** 2
    row_errors = feature_errors.mean(axis=1)
    return row_errors, feature_errors, x_scaled, scaler, pca


def _status(lsi: float) -> str:
    if lsi >= 70.0:
        return "red"
    if lsi >= 40.0:
        return "yellow"
    return "green"


def _module_error_scores(feature_cols: list[str], feature_errors_row: np.ndarray, lsi: float) -> tuple[dict[str, float], dict[str, float]]:
    by_feature = dict(zip(feature_cols, feature_errors_row, strict=False))
    raw_module_errors: dict[str, float] = {}
    for module_id, cols in MODULE_FEATURES.items():
        existing = [col for col in cols if col in by_feature]
        raw_module_errors[module_id] = float(np.mean([by_feature[col] for col in existing])) if existing else 0.0

    total_error = sum(raw_module_errors.values())
    if total_error <= 0:
        return ({m: 0.0 for m in MODULE_FEATURES}, {m: 0.0 for m in MODULE_FEATURES})

    contributions = {m: round(err / total_error * lsi, 4) for m, err in raw_module_errors.items()}
    scores = {m: round(min(100.0, err / total_error * 100.0), 4) for m, err in raw_module_errors.items()}
    return scores, contributions


def calculate_pca_lsi_history(
    df: pd.DataFrame,
    *,
    n_components: int = DEFAULT_N_COMPONENTS,
    error_quantile: float = DEFAULT_ERROR_QUANTILE,
) -> pd.DataFrame:
    feature_cols = get_feature_columns(df)
    row_errors, feature_errors, _, _, _ = _fit_reconstruct(df, feature_cols, n_components=n_components)
    scale = float(np.nanquantile(row_errors, error_quantile))
    if not np.isfinite(scale) or scale <= 0:
        scale = float(np.nanmax(row_errors)) or 1.0

    lsi_values = np.clip(row_errors / scale * 100.0, 0.0, 100.0)
    out = pd.DataFrame()
    if "date" in df.columns:
        out["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)
    else:
        # Dataset currently has no explicit date; keep deterministic row id for history plots.
        out["date"] = df.get("Unnamed: 0", pd.Series(range(len(df)))).astype(str)
    out["calculated_at"] = datetime.now(timezone.utc).isoformat()
    out["reconstruction_error"] = row_errors
    out["LSI"] = np.round(lsi_values, 2)
    out["status"] = out["LSI"].map(_status)
    out["confidence"] = 0.75

    module_scores = []
    module_contribs = []
    for i, lsi in enumerate(lsi_values):
        scores, contribs = _module_error_scores(feature_cols, feature_errors[i], float(lsi))
        module_scores.append(scores)
        module_contribs.append(contribs)
    for module_id in MODULE_FEATURES:
        out[f"{module_id}_score"] = [item[module_id] for item in module_scores]
        out[f"{module_id}_contribution"] = [item[module_id] for item in module_contribs]
    return out


def calculate_lsi_from_latest_row(df: pd.DataFrame) -> PCALSIResult:
    history = calculate_pca_lsi_history(df)
    latest = history.iloc[-1]
    original_latest = df.iloc[-1]
    active_flags = [col for col in FLAG_COLUMNS if col in original_latest.index and bool(original_latest[col])]
    warnings: list[str] = []
    if "Flag_PeresprosMAD_score_CBR" in df.columns:
        warnings.append("Column Flag_PeresprosMAD_score_CBR looks merged/ambiguous; treated as M3 Flag_Perespros for MVP and M5 MAD_score_CBR fallback remains neutral.")
    if "date" not in df.columns:
        warnings.append("PCA dataset has no explicit date column; latest row id is used as date for dashboard history.")
    scores = {m: float(latest[f"{m}_score"]) for m in MODULE_FEATURES}
    contribs = {m: float(latest[f"{m}_contribution"]) for m in MODULE_FEATURES}
    return PCALSIResult(
        date=str(latest["date"]),
        lsi=float(latest["LSI"]),
        status=str(latest["status"]),
        confidence=float(latest["confidence"]),
        module_scores=scores,
        module_contributions=contribs,
        active_flags=active_flags,
        warnings=warnings,
    )
