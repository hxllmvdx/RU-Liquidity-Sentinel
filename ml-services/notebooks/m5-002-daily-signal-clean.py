# %%
"""
M5-002: Daily signal table and dashboards for RU Liquidity Sentinel M5 Treasury.

Purpose:
    Convert M5 daily features into wide-format daily signals and dashboard data.

Outputs:
    data/processed/m5_treasury_daily_signals.csv
    data/processed/m5_treasury_dashboard.csv
    data/processed/m5_treasury_signal_summary.csv
    data/processed/m5_treasury_*_dashboard.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# %%
# -----------------------------------------------------------------------------
# Imports and config
# -----------------------------------------------------------------------------
MODULE_ID = "M5_TREASURY"

PROCESSED_DIR = Path("../data/processed")
FEATURES_INPUT_PATH = PROCESSED_DIR / "m5_treasury_daily_features.csv"
SIGNALS_OUTPUT_PATH = PROCESSED_DIR / "m5_treasury_daily_signals.csv"
DASHBOARD_OUTPUT_PATH = PROCESSED_DIR / "m5_treasury_dashboard.csv"
SUMMARY_OUTPUT_PATH = PROCESSED_DIR / "m5_treasury_signal_summary.csv"

BALANCE_PNG_PATH = PROCESSED_DIR / "m5_treasury_balance_dashboard.png"
DELTA_PNG_PATH = PROCESSED_DIR / "m5_treasury_delta_dashboard.png"
MAD_PNG_PATH = PROCESSED_DIR / "m5_treasury_mad_scores_dashboard.png"
PLACEMENTS_PNG_PATH = PROCESSED_DIR / "m5_treasury_placements_dashboard.png"

BUDGET_DRAIN_THRESHOLD_BLN_RUB = 300.0
MAD_WINDOW_DAYS = 1095
MAD_MIN_PERIODS = 30
MAD_DENOMINATOR_FLOOR = 1.0
PLOT_MAD_CLIP = 10


# %%
# -----------------------------------------------------------------------------
# Path helpers
# -----------------------------------------------------------------------------
def candidate_roots() -> list[Path]:
    roots = [
        Path.cwd().resolve(),
        *Path.cwd().resolve().parents,
        Path("/mnt/data"),
    ]
    result: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            result.append(root)
            seen.add(root)
    return result


def resolve_project_paths() -> dict[str, Path]:
    candidates = [root / FEATURES_INPUT_PATH for root in candidate_roots()]
    features_path = next((path for path in candidates if path.exists()), None)
    if features_path is None:
        raise FileNotFoundError(
            "Daily M5 features not found. Run m5-001 first. Searched:\n"
            + "\n".join(map(str, candidates))
        )

    roots = sorted(candidate_roots(), key=lambda r: len(str(r)), reverse=True)
    root = next(
        (root for root in roots if str(features_path).startswith(str(root))),
        Path.cwd().resolve(),
    )
    # Avoid selecting filesystem root when running scripts from / in a sandbox.
    if str(features_path).startswith("/mnt/data"):
        root = Path("/mnt/data")
    processed_dir = root / PROCESSED_DIR
    processed_dir.mkdir(parents=True, exist_ok=True)
    return {
        "features": features_path,
        "signals": processed_dir / SIGNALS_OUTPUT_PATH.name,
        "dashboard": processed_dir / DASHBOARD_OUTPUT_PATH.name,
        "summary": processed_dir / SUMMARY_OUTPUT_PATH.name,
        "balance_png": processed_dir / BALANCE_PNG_PATH.name,
        "delta_png": processed_dir / DELTA_PNG_PATH.name,
        "mad_png": processed_dir / MAD_PNG_PATH.name,
        "placements_png": processed_dir / PLACEMENTS_PNG_PATH.name,
    }


PATHS = resolve_project_paths()
print("Features input path:", PATHS["features"])


# %%
# -----------------------------------------------------------------------------
# Load daily features
# -----------------------------------------------------------------------------
def load_daily_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "date" not in df.columns:
        raise ValueError("date column is required in daily features.")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if "module_id" not in df.columns:
        df["module_id"] = MODULE_ID

    text_cols = {
        "module_id",
        "last_cbr_update_date",
        "last_roskazna_event_date",
    }
    for col in df.columns:
        if col != "date" and col not in text_cols:
            if col.startswith("has_") or col.startswith("Flag_"):
                df[col] = (
                    df[col].astype(str).str.lower().isin(["true", "1", "yes"])
                )
            else:
                converted = pd.to_numeric(df[col], errors="coerce")
                if converted.notna().sum() > 0:
                    df[col] = converted
    return df


features = load_daily_features(PATHS["features"])
print("Features loaded:", features.shape)
print("Date range:", features["date"].min(), "->", features["date"].max())
print("Missing values:")
print(features.isna().sum().sort_values(ascending=False))
print("Columns:", list(features.columns))


# %%
# -----------------------------------------------------------------------------
# MAD helper
# -----------------------------------------------------------------------------
def rolling_mad_score_no_lookahead(
    series: pd.Series,
    window_days: int = MAD_WINDOW_DAYS,
    min_periods: int = MAD_MIN_PERIODS,
    denominator_floor: float | None = MAD_DENOMINATOR_FLOOR,
) -> tuple[pd.Series, pd.Series]:
    """Return no-lookahead robust MAD score and per-row quality label."""
    x = pd.to_numeric(series, errors="coerce")
    history = x.shift(1)

    rolling_median = history.rolling(
        window_days, min_periods=min_periods
    ).median()

    def _mad(values: np.ndarray) -> float:
        s = pd.Series(values).dropna()
        if s.empty:
            return np.nan
        med = s.median()
        return float((s - med).abs().median())

    rolling_mad = history.rolling(window_days, min_periods=min_periods).apply(
        _mad, raw=True
    )
    denom = 1.4826 * rolling_mad
    if denominator_floor is not None:
        denom = denom.mask(denom.abs() < denominator_floor, denominator_floor)
    rolling_score = (x - rolling_median) / denom

    expanding_median = history.expanding(min_periods=min_periods).median()
    expanding_mad = history.expanding(min_periods=min_periods).apply(
        _mad, raw=True
    )
    expanding_denom = 1.4826 * expanding_mad
    if denominator_floor is not None:
        expanding_denom = expanding_denom.mask(
            expanding_denom.abs() < denominator_floor, denominator_floor
        )
    expanding_score = (x - expanding_median) / expanding_denom

    score = rolling_score.copy()
    quality = pd.Series("ok_rolling", index=x.index, dtype="object")
    fallback_mask = score.isna() & expanding_score.notna()
    score = score.where(~fallback_mask, expanding_score)
    quality.loc[fallback_mask] = "expanding_fallback"

    missing_input_mask = x.isna()
    quality.loc[missing_input_mask] = "missing_input_neutral_fill"

    neutral_mask = (
        score.replace([np.inf, -np.inf], np.nan).isna() & ~missing_input_mask
    )
    quality.loc[neutral_mask] = "neutral_fill_zero"

    score = score.replace([np.inf, -np.inf], np.nan)
    return score, quality


# %%
# -----------------------------------------------------------------------------
# Signal calculation
# -----------------------------------------------------------------------------
signals_source = features.copy()

if "budget_drain_bln_rub" not in signals_source.columns:
    if "cbr_weekly_delta_bln_rub" in signals_source.columns:
        signals_source["budget_drain_bln_rub"] = np.maximum(
            -signals_source["cbr_weekly_delta_bln_rub"], 0.0
        )
    else:
        signals_source["budget_drain_bln_rub"] = np.nan

cbr_stress_feature = signals_source["budget_drain_bln_rub"]
mad_cbr_raw, mad_cbr_quality = rolling_mad_score_no_lookahead(
    cbr_stress_feature
)
signals_source["MAD_score_CBR"] = mad_cbr_raw
signals_source["MAD_score_CBR_quality"] = mad_cbr_quality

if "roskazna_placement_7d_sum" in signals_source.columns:
    baseline_30d = (
        signals_source["roskazna_placement_7d_sum"]
        .shift(1)
        .rolling(30, min_periods=7)
        .median()
    )
    baseline_365d = (
        signals_source["roskazna_placement_7d_sum"]
        .shift(1)
        .rolling(365, min_periods=30)
        .median()
    )
    baseline = baseline_30d.fillna(baseline_365d)
    signals_source["roskazna_placement_drop_bln_rub"] = np.maximum(
        baseline - signals_source["roskazna_placement_7d_sum"], 0.0
    )
else:
    print(
        "WARNING: roskazna_placement_7d_sum missing; Roskazna MAD will be neutral-filled."
    )
    signals_source["roskazna_placement_drop_bln_rub"] = np.nan

mad_roskazna_raw, mad_roskazna_quality = rolling_mad_score_no_lookahead(
    signals_source["roskazna_placement_drop_bln_rub"]
)
signals_source["MAD_score_Roskazna"] = mad_roskazna_raw
signals_source["MAD_score_Roskazna_quality"] = mad_roskazna_quality

signals_source["Flag_Budget_Drain"] = signals_source["MAD_score_CBR"] >= 3.0
if "roskazna_placement_drop_bln_rub" in signals_source.columns:
    signals_source["Flag_Treasury_Placement_Drop"] = (
        signals_source["roskazna_placement_drop_bln_rub"].fillna(0).ge(300.0)
    )

# %%
# -----------------------------------------------------------------------------
# Fill missing signal values for final daily signal table
# -----------------------------------------------------------------------------
print("NaN coverage before fill:")
print(signals_source[["MAD_score_CBR", "MAD_score_Roskazna"]].isna().mean())

signals_source["MAD_score_CBR"] = signals_source["MAD_score_CBR"].fillna(0.0)
signals_source["MAD_score_Roskazna"] = signals_source[
    "MAD_score_Roskazna"
].fillna(0.0)
signals_source["Flag_Budget_Drain"] = (
    signals_source["Flag_Budget_Drain"].fillna(False).astype(bool)
)
if "Flag_Treasury_Placement_Drop" in signals_source.columns:
    signals_source["Flag_Treasury_Placement_Drop"] = (
        signals_source["Flag_Treasury_Placement_Drop"]
        .fillna(False)
        .astype(bool)
    )

print("NaN coverage after fill:")
print(signals_source[["MAD_score_CBR", "MAD_score_Roskazna"]].isna().mean())
print(
    "Flag_Budget_Drain count:", int(signals_source["Flag_Budget_Drain"].sum())
)

# %%
# -----------------------------------------------------------------------------
# Signals output format
# -----------------------------------------------------------------------------
signal_columns = [
    "date",
    "module_id",
    "MAD_score_CBR",
    "MAD_score_Roskazna",
    "Flag_Budget_Drain",
    "Flag_Treasury_Placement_Drop",
]
signal_columns = [
    col for col in signal_columns if col in signals_source.columns
]
signals = signals_source[signal_columns].copy()
signals.to_csv(PATHS["signals"], index=False)
print("Signal columns:", signal_columns)
print("Saved signals:", PATHS["signals"])

# %%
# -----------------------------------------------------------------------------
# Dashboard dataset
# -----------------------------------------------------------------------------
dashboard_columns = [
    "date",
    "module_id",
    "cbr_eks_balance_bln_rub",
    "structural_liquidity_balance_bln_rub",
    "participant_banks_count",
    "roskazna_deposit_placements_bln_rub",
    "roskazna_placement_7d_sum",
    "roskazna_placement_30d_sum",
    "cbr_weekly_delta_bln_rub",
    "cbr_monthly_delta_bln_rub",
    "budget_drain_bln_rub",
    "roskazna_placement_drop_bln_rub",
    "MAD_score_CBR",
    "MAD_score_Roskazna",
    "MAD_score_CBR_quality",
    "MAD_score_Roskazna_quality",
    "Flag_Budget_Drain",
    "Flag_Treasury_Placement_Drop",
    "has_cbr_update",
    "has_roskazna_event",
    "days_since_cbr_update",
    "days_since_roskazna_event",
]
dashboard_columns = [
    col for col in dashboard_columns if col in signals_source.columns
]
dashboard = signals_source[dashboard_columns].copy()
dashboard.to_csv(PATHS["dashboard"], index=False)
print("Saved dashboard:", PATHS["dashboard"])

# %%
# -----------------------------------------------------------------------------
# Graph 1: M5 Treasury balance
# -----------------------------------------------------------------------------
plt.figure(figsize=(16, 5))
if "cbr_eks_balance_bln_rub" in dashboard.columns:
    plt.plot(
        dashboard["date"],
        dashboard["cbr_eks_balance_bln_rub"],
        label="CBR EKS balance, bln RUB",
    )
if "structural_liquidity_balance_bln_rub" in dashboard.columns:
    plt.plot(
        dashboard["date"],
        dashboard["structural_liquidity_balance_bln_rub"],
        label="Structural liquidity, bln RUB",
    )
plt.title("M5 Treasury balance")
plt.xlabel("Date")
plt.ylabel("bln RUB")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(PATHS["balance_png"], dpi=160)
plt.show()
print("Saved chart:", PATHS["balance_png"])

# %%
# -----------------------------------------------------------------------------
# Graph 2: M5 Treasury deltas / budget drain
# -----------------------------------------------------------------------------
plt.figure(figsize=(16, 5))
if "cbr_weekly_delta_bln_rub" in dashboard.columns:
    plt.plot(
        dashboard["date"],
        dashboard["cbr_weekly_delta_bln_rub"],
        label="CBR weekly delta, bln RUB",
    )
if "cbr_monthly_delta_bln_rub" in dashboard.columns:
    plt.plot(
        dashboard["date"],
        dashboard["cbr_monthly_delta_bln_rub"],
        label="CBR monthly delta, bln RUB",
        alpha=0.75,
    )
plt.axhline(
    -BUDGET_DRAIN_THRESHOLD_BLN_RUB,
    linestyle="--",
    linewidth=1,
    label="Weekly drain threshold: -300 bln RUB",
)
flagged = dashboard[dashboard["Flag_Budget_Drain"]]
if not flagged.empty and "cbr_weekly_delta_bln_rub" in dashboard.columns:
    plt.scatter(
        flagged["date"],
        flagged["cbr_weekly_delta_bln_rub"],
        label="Flag_Budget_Drain",
        zorder=3,
    )
plt.title("M5 Treasury deltas / budget drain")
plt.xlabel("Date")
plt.ylabel("bln RUB")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(PATHS["delta_png"], dpi=160)
plt.show()
print("Saved chart:", PATHS["delta_png"])

# %%
# -----------------------------------------------------------------------------
# Graph 3: M5 MAD stress signals
# -----------------------------------------------------------------------------
plt.figure(figsize=(16, 5))
plot_mad_cbr = dashboard["MAD_score_CBR"].clip(-PLOT_MAD_CLIP, PLOT_MAD_CLIP)
plot_mad_roskazna = dashboard["MAD_score_Roskazna"].clip(
    -PLOT_MAD_CLIP, PLOT_MAD_CLIP
)
plt.plot(
    dashboard["date"],
    plot_mad_cbr,
    label=f"MAD_score_CBR clipped to ±{PLOT_MAD_CLIP}",
)
plt.plot(
    dashboard["date"],
    plot_mad_roskazna,
    label=f"MAD_score_Roskazna clipped to ±{PLOT_MAD_CLIP}",
)
plt.axhline(2, linestyle="--", linewidth=1, label="+2 MAD")
plt.axhline(-2, linestyle="--", linewidth=1, label="-2 MAD")
plt.title("M5 MAD stress signals — clipping only for visualization")
plt.xlabel("Date")
plt.ylabel("MAD score")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(PATHS["mad_png"], dpi=160)
plt.show()
print("Saved chart:", PATHS["mad_png"])

# %%
# -----------------------------------------------------------------------------
# Graph 4: M5 Roskazna placements
# -----------------------------------------------------------------------------
plt.figure(figsize=(16, 5))
if "roskazna_deposit_placements_bln_rub" in dashboard.columns:
    weekly_placements = (
        dashboard.set_index("date")["roskazna_deposit_placements_bln_rub"]
        .resample("W")
        .sum()
    )
    plt.bar(
        weekly_placements.index,
        weekly_placements.values,
        width=5,
        alpha=0.35,
        label="Weekly Roskazna placements, bln RUB",
    )
if "roskazna_placement_7d_sum" in dashboard.columns:
    plt.plot(
        dashboard["date"],
        dashboard["roskazna_placement_7d_sum"],
        label="7d placement sum, bln RUB",
    )
if "roskazna_placement_30d_sum" in dashboard.columns:
    plt.plot(
        dashboard["date"],
        dashboard["roskazna_placement_30d_sum"],
        label="30d placement sum, bln RUB",
    )
plt.title("M5 Roskazna placements")
plt.xlabel("Date")
plt.ylabel("bln RUB")
plt.grid(alpha=0.25)
plt.legend()
plt.tight_layout()
plt.savefig(PATHS["placements_png"], dpi=160)
plt.show()
print("Saved chart:", PATHS["placements_png"])

# %%
# -----------------------------------------------------------------------------
# Summary output
# -----------------------------------------------------------------------------
summary = pd.DataFrame(
    [
        {
            "rows": len(signals_source),
            "date_min": signals_source["date"].min().date().isoformat(),
            "date_max": signals_source["date"].max().date().isoformat(),
            "MAD_score_CBR_coverage": float(
                signals_source["MAD_score_CBR"].notna().mean()
            ),
            "MAD_score_Roskazna_coverage": float(
                signals_source["MAD_score_Roskazna"].notna().mean()
            ),
            "Flag_Budget_Drain_count": int(
                signals_source["Flag_Budget_Drain"].sum()
            ),
            "has_cbr_update_count": int(
                signals_source.get(
                    "has_cbr_update",
                    pd.Series(False, index=signals_source.index),
                ).sum()
            ),
            "has_roskazna_event_count": int(
                signals_source.get(
                    "has_roskazna_event",
                    pd.Series(False, index=signals_source.index),
                ).sum()
            ),
            "max_budget_drain_bln_rub": float(
                signals_source["budget_drain_bln_rub"].max(skipna=True)
            )
            if "budget_drain_bln_rub" in signals_source
            else np.nan,
            "max_abs_MAD_score_CBR": float(
                signals_source["MAD_score_CBR"].abs().max(skipna=True)
            ),
            "max_abs_MAD_score_Roskazna": float(
                signals_source["MAD_score_Roskazna"].abs().max(skipna=True)
            ),
        }
    ]
)
summary.to_csv(PATHS["summary"], index=False)
print("Saved summary:", PATHS["summary"])
print("Output paths:")
for name, path in PATHS.items():
    if name != "features":
        print(f"- {name}: {path}")
