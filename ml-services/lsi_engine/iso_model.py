"""IsolationForest-based LSI model.

Mirrors the standalone training script (iso_model2.py) and prediction
helper (predict.py) provided by the analyst, wired into the ml-services
pipeline so the model is trained on container startup and reused for
LSI scoring across the dashboard / history / snapshot paths.

Public entry points:
    bootstrap_train_if_needed() -> Path
        Called at gRPC server startup. Trains the model from
        data/processed/all_df_date.csv if persisted artifacts are
        missing or stale, otherwise reuses them.

    lookup_lsi_by_date(date_str) -> float | None
        Returns precomputed LSI for a known historical date.

    predict_for_snapshot(snapshot) -> float | None
        Predicts LSI for an arbitrary feature snapshot (dict). Used
        when scoring the latest recalculation or scenarios for dates
        not present in the historical CSV.

    is_available() -> bool
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

logger = logging.getLogger(__name__)

MODULE_WEIGHTS = {"M1": 0.30, "M2": 0.25, "M3": 0.20, "M4": 0.15, "M5": 0.10}
SMOOTHING_SPAN = 3
MODEL_VERSION = "isolation-forest-lsi-v2"

M1_COLS = ["mad_score_ruonia", "mad_score_spread", "flag_end_period"]
M2_COLS = ["MAD_score_rate_spread", "MAD_score_cover", "Flag_Demand", "MAD_score_repo_volume"]
M3_COLS = ["MAD_score_yield_spread", "Flag_Nedospros", "Flag_Perespros", "MAD_score_cover_m3"]
M4_COLS = ["Tax_Week_Flag", "End_of_Month_Flag", "End_of_Quarter_Flag", "Seasonal_Factor"]
M5_COLS = ["MAD_score_CBR", "MAD_score_Roskazna", "Flag_Budget_Drain", "Flag_Treasury_Placement_Drop"]
ALL_COLS = M1_COLS + M2_COLS + M4_COLS + M3_COLS + M5_COLS
MODULE_COLS = ["M1_score", "M2_score", "M3_score", "M4_score", "M5_score"]
EXCLUDE = {"date", "LSI", "LSI_STATUS", "base_LSI", "anomaly_score", "anomaly_score_smooth"}

# Map prefixed snapshot keys (used everywhere in formula.py and the wide
# dataset) back to the raw CSV column names the model was trained on.
SNAPSHOT_KEY_TO_RAW = {
    "M1_MAD_score_RUONIA": "mad_score_ruonia",
    "M1_MAD_score_spread": "mad_score_spread",
    "M1_Flag_EndOfPeriod": "flag_end_period",
    "M2_MAD_score_rate_spread": "MAD_score_rate_spread",
    "M2_MAD_score_cover": "MAD_score_cover",
    "M2_Flag_Demand": "Flag_Demand",
    "M2_MAD_score_repo_volume": "MAD_score_repo_volume",
    "M3_MAD_score_yield_spread": "MAD_score_yield_spread",
    "M3_Flag_Nedospros": "Flag_Nedospros",
    "M3_Flag_Perespros": "Flag_Perespros",
    "M3_MAD_score_cover": "MAD_score_cover_m3",
    "M4_Tax_Week_Flag": "Tax_Week_Flag",
    "M4_End_of_Month_Flag": "End_of_Month_Flag",
    "M4_End_of_Quarter_Flag": "End_of_Quarter_Flag",
    "M4_Seasonal_Factor": "Seasonal_Factor",
    "M5_MAD_score_CBR": "MAD_score_CBR",
    "M5_MAD_score_Roskazna": "MAD_score_Roskazna",
    "M5_Flag_Budget_Drain": "Flag_Budget_Drain",
    "M5_Flag_Treasury_Placement_Drop": "Flag_Treasury_Placement_Drop",
}

_TRAIN_LOCK = threading.Lock()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_dir() -> Path:
    path = repo_root() / "data" / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dataset_path() -> Path:
    candidates = [
        repo_root() / "data" / "processed" / "all_df_date.csv",
        repo_root() / "ml-services" / "data" / "processed" / "all_df_date.csv",
        Path("/app/data/processed/all_df_date.csv"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("all_df_date.csv not found in " + ", ".join(str(c) for c in candidates))


def _artifact_paths() -> dict[str, Path]:
    base = _model_dir()
    return {
        "iso": base / "iso_model.pkl",
        "scaler": base / "scaler.pkl",
        "features": base / "features.pkl",
        "lsi_min": base / "lsi_min.pkl",
        "lsi_max": base / "lsi_max.pkl",
        "history_lsi": base / "history_lsi.pkl",
    }


def _bool_to_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "yes", "y", "да"} else 0
    if pd.isna(value):
        return 0
    return int(bool(value))


def _robust_zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    median = s.median()
    mad = np.median(np.abs(s - median))
    if mad == 0 or np.isnan(mad):
        return pd.Series(0.0, index=s.index)
    return ((s - median) / (1.4826 * mad)).fillna(0)


def _normalize_0_100(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    smin = float(s.min())
    smax = float(s.max())
    if smax - smin == 0:
        return pd.Series(50.0, index=s.index)
    return (100.0 * (s - smin) / (smax - smin)).fillna(50)


def _build_module_score(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    z = pd.concat([_robust_zscore(df[col]) for col in cols], axis=1).mean(axis=1)
    return _normalize_0_100(z)


def _prepare_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Replicates the feature engineering from iso_model2.py."""
    df = raw_df.copy()
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    for col in ALL_COLS:
        if col not in df.columns:
            df[col] = 0
    for col in ["Flag_Demand", "Flag_Nedospros", "Flag_Perespros",
                "Tax_Week_Flag", "End_of_Month_Flag", "End_of_Quarter_Flag",
                "flag_end_period", "Flag_Budget_Drain", "Flag_Treasury_Placement_Drop"]:
        df[col] = df[col].map(_bool_to_int)
    df[ALL_COLS] = df[ALL_COLS].replace([np.inf, -np.inf], np.nan).fillna(0)

    df["M1_score"] = _build_module_score(df, M1_COLS)
    df["M2_score"] = _build_module_score(df, M2_COLS)
    df["M3_score"] = _build_module_score(df, M3_COLS)
    df["M4_score"] = _build_module_score(df, M4_COLS)
    df["M5_score"] = _build_module_score(df, M5_COLS)

    df[MODULE_COLS] = df[MODULE_COLS].replace([np.inf, -np.inf], np.nan).fillna(50)
    for col in MODULE_COLS:
        df[col] = df[col].ewm(span=5).mean()

    df["base_LSI"] = sum(MODULE_WEIGHTS[m[:2]] * df[m] for m in MODULE_COLS)

    for col in ALL_COLS:
        df[f"{col}_mean_14"] = df[col].rolling(14, min_periods=1).mean()
        df[f"{col}_std_14"] = df[col].rolling(14, min_periods=1).std().fillna(0)
        df[f"{col}_diff_7"] = df[col].diff(7).fillna(0)

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)


def _predict_series(prepared_df: pd.DataFrame, iso, scaler, features, lsi_min: float, lsi_max: float) -> pd.Series:
    x = prepared_df[features].replace([np.inf, -np.inf], np.nan).fillna(0)
    x_scaled = scaler.transform(x)
    anomaly = pd.Series(iso.score_samples(x_scaled))
    smooth = anomaly.ewm(span=SMOOTHING_SPAN).mean()
    if_signal = -smooth
    if lsi_max - lsi_min == 0:
        normalized = pd.Series(50.0, index=if_signal.index)
    else:
        normalized = 100.0 * (if_signal - lsi_min) / (lsi_max - lsi_min)
    return normalized.clip(0, 100).fillna(50)


def train_and_persist(force: bool = False) -> dict[str, Any]:
    """Train IsolationForest on all_df_date.csv and persist artifacts.

    If `force=False` and all artifact files are newer than the CSV,
    training is skipped.
    """
    with _TRAIN_LOCK:
        paths = _artifact_paths()
        csv_path = _dataset_path()
        if not force and all(p.exists() for p in paths.values()):
            csv_mtime = csv_path.stat().st_mtime
            if all(p.stat().st_mtime >= csv_mtime for p in paths.values()):
                logger.info("LSI model artifacts already up to date at %s", _model_dir())
                _cached_artifacts.cache_clear()
                return {"trained": False, "artifacts": str(_model_dir())}

        logger.info("Training IsolationForest LSI model from %s", csv_path)
        raw = pd.read_csv(csv_path)
        prepared = _prepare_features(raw)
        features = [c for c in prepared.columns if c not in EXCLUDE]
        x = prepared[features].replace([np.inf, -np.inf], np.nan).fillna(0)

        scaler = RobustScaler()
        x_scaled = scaler.fit_transform(x)

        iso = IsolationForest(n_estimators=700, contamination=0.01, random_state=42, n_jobs=-1)
        iso.fit(x_scaled)

        # Capture min/max of smoothed -anomaly_score for future single-row
        # normalization (replicates the implicit normalization in predict.py
        # over the historical fit set).
        anomaly = pd.Series(iso.score_samples(x_scaled))
        smooth = anomaly.ewm(span=SMOOTHING_SPAN).mean()
        if_signal = -smooth
        lsi_min = float(if_signal.min())
        lsi_max = float(if_signal.max())

        lsi_series = _predict_series(prepared, iso, scaler, features, lsi_min, lsi_max)
        history_lsi = {
            pd.to_datetime(prepared.loc[i, "date"]).strftime("%Y-%m-%d"): float(lsi_series.iloc[i])
            for i in range(len(prepared))
        }

        joblib.dump(iso, paths["iso"])
        joblib.dump(scaler, paths["scaler"])
        joblib.dump(features, paths["features"])
        joblib.dump(lsi_min, paths["lsi_min"])
        joblib.dump(lsi_max, paths["lsi_max"])
        joblib.dump(history_lsi, paths["history_lsi"])
        logger.info("LSI model trained on %s rows, persisted to %s", len(prepared), _model_dir())
        _cached_artifacts.cache_clear()
        return {"trained": True, "rows": int(len(prepared)), "artifacts": str(_model_dir())}


@lru_cache(maxsize=1)
def _cached_artifacts() -> dict[str, Any] | None:
    paths = _artifact_paths()
    if not all(p.exists() for p in paths.values()):
        return None
    try:
        return {
            "iso": joblib.load(paths["iso"]),
            "scaler": joblib.load(paths["scaler"]),
            "features": joblib.load(paths["features"]),
            "lsi_min": float(joblib.load(paths["lsi_min"])),
            "lsi_max": float(joblib.load(paths["lsi_max"])),
            "history_lsi": joblib.load(paths["history_lsi"]),
        }
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to load LSI model artifacts: %s", exc)
        return None


def is_available() -> bool:
    return _cached_artifacts() is not None


def bootstrap_train_if_needed() -> dict[str, Any]:
    try:
        return train_and_persist(force=False)
    except Exception as exc:  # pragma: no cover
        logger.exception("LSI model training at startup failed: %s", exc)
        return {"trained": False, "error": str(exc)}


def lookup_lsi_by_date(date_str: str | None) -> float | None:
    if not date_str:
        return None
    arts = _cached_artifacts()
    if arts is None:
        return None
    history = arts["history_lsi"]
    key = str(date_str)[:10]
    value = history.get(key)
    return float(value) if value is not None else None


def _snapshot_to_raw_row(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Map a snapshot dict (with Mx_-prefixed keys) into the raw CSV schema."""
    raw: dict[str, Any] = {}
    for prefixed, raw_key in SNAPSHOT_KEY_TO_RAW.items():
        if prefixed in snapshot and snapshot[prefixed] is not None:
            raw[raw_key] = snapshot[prefixed]
        elif raw_key in snapshot and snapshot[raw_key] is not None:
            raw[raw_key] = snapshot[raw_key]
        else:
            raw[raw_key] = 0
    raw["date"] = snapshot.get("date")
    return raw


def predict_lsi_for_wide_df(wide_df: "pd.DataFrame") -> dict[str, float]:
    """Predict an LSI series for the wide dataset built by
    `pipeline.build_wide_dataset.build_wide_lsi_dataset`.

    The wide dataset uses Mx_-prefixed column names. We translate them to
    the raw schema the model was trained on, recompute features
    *over the whole wide_df* (so rolling/diff features vary per-row),
    then run a single batch prediction. Returns a date(YYYY-MM-DD) -> LSI
    mapping.

    This is the path actually used by the dashboard / backtest / history
    flow — `lookup_lsi_by_date` consults this result.
    """
    arts = _cached_artifacts()
    if arts is None or wide_df is None or len(wide_df) == 0:
        return {}
    try:
        raw_rows = []
        for _, src in wide_df.iterrows():
            row = {raw: 0 for raw in ALL_COLS}
            for prefixed, raw_key in SNAPSHOT_KEY_TO_RAW.items():
                if prefixed in src and pd.notna(src[prefixed]):
                    row[raw_key] = src[prefixed]
                elif raw_key in src and pd.notna(src[raw_key]):
                    row[raw_key] = src[raw_key]
            row["date"] = src.get("date")
            raw_rows.append(row)
        raw_df = pd.DataFrame(raw_rows)
        prepared = _prepare_features(raw_df)
        lsi_series = _predict_series(
            prepared,
            arts["iso"],
            arts["scaler"],
            arts["features"],
            arts["lsi_min"],
            arts["lsi_max"],
        )
        out: dict[str, float] = {}
        for i in range(len(prepared)):
            d = pd.to_datetime(prepared.loc[i, "date"]).strftime("%Y-%m-%d")
            out[d] = float(lsi_series.iloc[i])
        # Augment the cached history_lsi dict so future single-snapshot lookups hit it too.
        try:
            arts["history_lsi"].update(out)
        except Exception:
            pass
        return out
    except Exception as exc:  # pragma: no cover
        logger.exception("predict_lsi_for_wide_df failed: %s", exc)
        return {}


def predict_for_snapshot(snapshot: dict[str, Any]) -> float | None:
    """Predict LSI for an arbitrary feature snapshot.

    Builds a single-row dataframe with the snapshot appended to the
    historical CSV (so rolling/diff features are meaningful) and returns
    the model-predicted LSI for that row.
    """
    arts = _cached_artifacts()
    if arts is None:
        return None
    try:
        raw_row = _snapshot_to_raw_row(snapshot)
        # Reuse history for rolling context.
        raw_history = pd.read_csv(_dataset_path())
        if "Unnamed: 0" in raw_history.columns:
            raw_history = raw_history.drop(columns=["Unnamed: 0"])
        # Only keep columns we need + date.
        keep_cols = ["date"] + ALL_COLS
        for c in keep_cols:
            if c not in raw_history.columns:
                raw_history[c] = 0
        raw_history = raw_history[keep_cols]
        # Append snapshot row.
        snap_df = pd.DataFrame([{c: raw_row.get(c, 0) for c in keep_cols}])
        combined = pd.concat([raw_history, snap_df], ignore_index=True)
        prepared = _prepare_features(combined)
        last = prepared.tail(1)
        x = last[arts["features"]].replace([np.inf, -np.inf], np.nan).fillna(0)
        # For a single row the smoothing is a no-op; reuse training min/max.
        x_scaled = arts["scaler"].transform(x)
        anomaly = float(arts["iso"].score_samples(x_scaled)[0])
        if_signal = -anomaly
        lsi_min = arts["lsi_min"]
        lsi_max = arts["lsi_max"]
        if lsi_max - lsi_min == 0:
            return 50.0
        lsi = 100.0 * (if_signal - lsi_min) / (lsi_max - lsi_min)
        return float(max(0.0, min(100.0, lsi)))
    except Exception as exc:  # pragma: no cover
        logger.exception("LSI model snapshot prediction failed: %s", exc)
        return None
