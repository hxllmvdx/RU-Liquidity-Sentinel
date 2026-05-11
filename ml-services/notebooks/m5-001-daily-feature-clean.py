# %%
"""
M5-001: Daily feature panel for RU Liquidity Sentinel M5 Treasury module.

Purpose:
    Build one-row-per-calendar-day feature table for the budget / treasury
    liquidity channel.

Outputs:
    data/processed/m5_treasury_daily_features.csv
    data/processed/m5_treasury_dashboard.csv
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
START_DATE = pd.Timestamp("2021-01-01")

RAW_OR_PROCESSED_INPUT_PATH = Path(
    "data/raw/treasury/m5_treasury/m5_treasury_features_2021-01-01_2026-05-10.csv"
)
FALLBACK_INPUT_PATHS = [
    Path("data/processed/treasury/m5_treasury/m5_treasury_feature_clean.csv"),
    Path(
        "data/processed/treasury/m5_treasury/m5_treasury_features_2021-01-01_2026-05-10.csv"
    ),
    Path("/mnt/data/m5_treasury_features_2021-01-01_2026-05-10.csv"),
]

PROCESSED_DIR = Path("data/processed")
FEATURES_OUTPUT_PATH = PROCESSED_DIR / "m5_treasury_daily_features.csv"
DASHBOARD_OUTPUT_PATH = PROCESSED_DIR / "m5_treasury_dashboard.csv"

RENAME_MAPPING = {
    "observation_date": "date",
    "federal_budget_and_extrabudgetary_funds_balances_bln_rub": "cbr_eks_balance_bln_rub",
    "eks_deposit_placement_volume_bln_rub": "roskazna_deposit_placements_bln_rub",
    "ground_truth_liquidity_bln_rub": "structural_liquidity_balance_bln_rub",
    "delta_week_bln_rub": "cbr_weekly_delta_bln_rub_source",
    "delta_month_bln_rub": "cbr_monthly_delta_bln_rub_source",
}

LEVEL_COLUMNS_CANDIDATES = [
    "cbr_eks_balance_bln_rub",
    "structural_liquidity_balance_bln_rub",
    "participant_banks_count",
]
EVENT_COLUMNS_CANDIDATES = ["roskazna_deposit_placements_bln_rub"]
TEXT_COLUMNS = {"source_code", "raw_refs", "loaded_at", "module_id"}


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
    input_candidates: list[Path] = []
    for root in candidate_roots():
        input_candidates.append(root / RAW_OR_PROCESSED_INPUT_PATH)
        input_candidates.extend(
            root / path
            for path in FALLBACK_INPUT_PATHS
            if not path.is_absolute()
        )
    input_candidates.extend(
        path for path in FALLBACK_INPUT_PATHS if path.is_absolute()
    )

    input_path = next(
        (path for path in input_candidates if path.exists()), None
    )
    if input_path is None:
        raise FileNotFoundError(
            "M5 input CSV not found. Searched:\n"
            + "\n".join(map(str, input_candidates))
        )

    root = next(
        (
            root
            for root in candidate_roots()
            if str(input_path).startswith(str(root))
        ),
        Path.cwd().resolve(),
    )
    if (
        str(input_path).startswith("/mnt/data")
        and not (Path.cwd() / "data").exists()
    ):
        root = Path("/mnt/data")

    processed_dir = root / PROCESSED_DIR
    return {
        "input": input_path,
        "processed_dir": processed_dir,
        "features": processed_dir / FEATURES_OUTPUT_PATH.name,
        "dashboard": processed_dir / DASHBOARD_OUTPUT_PATH.name,
    }


PATHS = resolve_project_paths()
PATHS["processed_dir"].mkdir(parents=True, exist_ok=True)
print("Input path:", PATHS["input"])
print("Processed dir:", PATHS["processed_dir"])


# %%
# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------
def load_m5_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(
        columns={k: v for k, v in RENAME_MAPPING.items() if k in df.columns}
    )

    if "date" not in df.columns:
        raise ValueError(
            "Required date column is missing after rename mapping."
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    for col in df.columns:
        if col != "date" and col not in TEXT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("date").reset_index(drop=True)
    return df


raw = load_m5_csv(PATHS["input"])

raw = raw.loc[raw["date"] >= START_DATE].copy()

print("Rows loaded:", len(raw))
print("Columns:", list(raw.columns))
print("Date range:", raw["date"].min(), "->", raw["date"].max())
print("Missing values:")
print(raw.isna().sum().sort_values(ascending=False))
print("Duplicate date rows:", int(raw.duplicated("date").sum()))

# %%
# -----------------------------------------------------------------------------
# Column classification
# -----------------------------------------------------------------------------
level_columns = [col for col in LEVEL_COLUMNS_CANDIDATES if col in raw.columns]
event_columns = [col for col in EVENT_COLUMNS_CANDIDATES if col in raw.columns]
missing_level = sorted(set(LEVEL_COLUMNS_CANDIDATES) - set(level_columns))
missing_event = sorted(set(EVENT_COLUMNS_CANDIDATES) - set(event_columns))
if missing_level:
    print("WARNING: missing level columns:", missing_level)
if missing_event:
    print("WARNING: missing event columns:", missing_event)
print("Level columns:", level_columns)
print("Event columns:", event_columns)


# %%
# -----------------------------------------------------------------------------
# Aggregate duplicate dates if needed
# -----------------------------------------------------------------------------
def aggregate_duplicate_dates(df: pd.DataFrame) -> pd.DataFrame:
    if not df.duplicated("date").any():
        return df

    print("WARNING: duplicate dates found. Aggregating by date.")
    agg: dict[str, str] = {}
    for col in df.columns:
        if col == "date":
            continue
        if col in event_columns:
            agg[col] = "sum"
        elif col in level_columns:
            agg[col] = "last"
        elif col.endswith("_source") or pd.api.types.is_numeric_dtype(df[col]):
            agg[col] = "last"
        else:
            agg[col] = "last"
    return (
        df.groupby("date", as_index=False)
        .agg(agg)
        .sort_values("date")
        .reset_index(drop=True)
    )


raw_daily = aggregate_duplicate_dates(raw)

# %%
# -----------------------------------------------------------------------------
# Build daily calendar
# -----------------------------------------------------------------------------
calendar = pd.DataFrame(
    {
        "date": pd.date_range(
            raw_daily["date"].min(), raw_daily["date"].max(), freq="D"
        )
    }
)
daily = calendar.merge(raw_daily, on="date", how="left")
daily["module_id"] = MODULE_ID
print("Daily calendar rows:", len(daily))
print("Daily date range:", daily["date"].min(), "->", daily["date"].max())

# %%
# -----------------------------------------------------------------------------
# Freshness flags before fill
# -----------------------------------------------------------------------------
daily["has_cbr_update"] = False
if level_columns:
    daily["has_cbr_update"] = daily[level_columns].notna().any(axis=1)

if "roskazna_deposit_placements_bln_rub" in daily.columns:
    daily["has_roskazna_event"] = (
        daily["roskazna_deposit_placements_bln_rub"].fillna(0).gt(0)
    )
else:
    daily["has_roskazna_event"] = False

# %%
# -----------------------------------------------------------------------------
# Fill daily panel correctly
# -----------------------------------------------------------------------------
for col in level_columns:
    daily[col] = daily[col].ffill()

for col in event_columns:
    daily[col] = daily[col].fillna(0.0)

for col in ["has_cbr_update", "has_roskazna_event"]:
    daily[col] = daily[col].fillna(False).astype(bool)

# Preserve optional source delta columns but do not use them as canonical daily deltas.
for source_col in [
    "cbr_weekly_delta_bln_rub_source",
    "cbr_monthly_delta_bln_rub_source",
    "roskazna_weekly_delta_bln_rub_source",
]:
    if source_col in daily.columns:
        daily[source_col] = pd.to_numeric(daily[source_col], errors="coerce")


# %%
# -----------------------------------------------------------------------------
# days_since features
# -----------------------------------------------------------------------------
def add_days_since(
    df: pd.DataFrame, flag_col: str, last_date_col: str, days_col: str
) -> pd.DataFrame:
    df = df.copy()
    event_dates = df["date"].where(df[flag_col])
    df[last_date_col] = event_dates.ffill()
    df[days_col] = (df["date"] - df[last_date_col]).dt.days
    df[days_col] = df[days_col].fillna(999).astype(int)
    df[last_date_col] = df[last_date_col].dt.strftime("%Y-%m-%d")
    return df


daily = add_days_since(
    daily, "has_cbr_update", "last_cbr_update_date", "days_since_cbr_update"
)
daily = add_days_since(
    daily,
    "has_roskazna_event",
    "last_roskazna_event_date",
    "days_since_roskazna_event",
)

# %%
# -----------------------------------------------------------------------------
# Rolling/event features
# -----------------------------------------------------------------------------
if "roskazna_deposit_placements_bln_rub" in daily.columns:
    daily["roskazna_placement_7d_sum"] = (
        daily["roskazna_deposit_placements_bln_rub"]
        .rolling(7, min_periods=1)
        .sum()
    )
    daily["roskazna_placement_30d_sum"] = (
        daily["roskazna_deposit_placements_bln_rub"]
        .rolling(30, min_periods=1)
        .sum()
    )
else:
    print(
        "WARNING: cannot calculate Roskazna rolling sums; placement column is missing."
    )

if "cbr_eks_balance_bln_rub" in daily.columns:
    daily["cbr_weekly_delta_bln_rub"] = daily[
        "cbr_eks_balance_bln_rub"
    ] - daily["cbr_eks_balance_bln_rub"].shift(7)
    daily["cbr_monthly_delta_bln_rub"] = daily[
        "cbr_eks_balance_bln_rub"
    ] - daily["cbr_eks_balance_bln_rub"].shift(30)
else:
    print(
        "WARNING: cannot calculate CBR deltas; cbr_eks_balance_bln_rub is missing."
    )

if "structural_liquidity_balance_bln_rub" in daily.columns:
    daily["structural_liquidity_weekly_delta_bln_rub"] = daily[
        "structural_liquidity_balance_bln_rub"
    ] - daily["structural_liquidity_balance_bln_rub"].shift(7)

if "participant_banks_count" in daily.columns:
    daily["participant_banks_count_change_30d"] = daily[
        "participant_banks_count"
    ] - daily["participant_banks_count"].shift(30)

# %%
# -----------------------------------------------------------------------------
# Budget drain feature
# -----------------------------------------------------------------------------
if "cbr_weekly_delta_bln_rub" in daily.columns:
    daily["budget_drain_bln_rub"] = np.where(
        daily["cbr_weekly_delta_bln_rub"].notna(),
        np.maximum(-daily["cbr_weekly_delta_bln_rub"], 0.0),
        np.nan,
    )
else:
    daily["budget_drain_bln_rub"] = np.nan

# %%
# -----------------------------------------------------------------------------
# Feature diagnostics
# -----------------------------------------------------------------------------
print("Feature panel shape:", daily.shape)
print("Date range:", daily["date"].min(), "->", daily["date"].max())
print("Coverage:")
print(daily.notna().mean().sort_values(ascending=False))
print("has_cbr_update days:", int(daily["has_cbr_update"].sum()))
print("has_roskazna_event days:", int(daily["has_roskazna_event"].sum()))

numeric_cols = daily.select_dtypes(include=[np.number]).columns.tolist()
core_numeric = [
    col
    for col in [
        "cbr_eks_balance_bln_rub",
        "structural_liquidity_balance_bln_rub",
        "participant_banks_count",
        "roskazna_deposit_placements_bln_rub",
        "roskazna_placement_7d_sum",
        "roskazna_placement_30d_sum",
        "cbr_weekly_delta_bln_rub",
        "cbr_monthly_delta_bln_rub",
        "budget_drain_bln_rub",
    ]
    if col in numeric_cols
]
print("Numeric diagnostics:")
print(
    daily[core_numeric].agg(["min", "max", "median"]).T
    if core_numeric
    else "No numeric diagnostics available"
)
for threshold in [300, 400, 500]:
    print(
        f"Potential Flag_Budget_Drain days >= {threshold}:",
        int(daily["budget_drain_bln_rub"].fillna(0).ge(threshold).sum()),
    )

# %%
# -----------------------------------------------------------------------------
# Export features
# -----------------------------------------------------------------------------
feature_columns = [
    "date",
    "module_id",
    "cbr_eks_balance_bln_rub",
    "structural_liquidity_balance_bln_rub",
    "participant_banks_count",
    "roskazna_deposit_placements_bln_rub",
    "roskazna_placement_7d_sum",
    "roskazna_placement_30d_sum",
    "has_cbr_update",
    "has_roskazna_event",
    "last_cbr_update_date",
    "days_since_cbr_update",
    "last_roskazna_event_date",
    "days_since_roskazna_event",
    "cbr_weekly_delta_bln_rub",
    "cbr_monthly_delta_bln_rub",
    "cbr_weekly_delta_bln_rub_source",
    "cbr_monthly_delta_bln_rub_source",
    "budget_drain_bln_rub",
    "structural_liquidity_weekly_delta_bln_rub",
    "participant_banks_count_change_30d",
]
feature_columns = [col for col in feature_columns if col in daily.columns]
features = daily[feature_columns].copy()
features.to_csv(PATHS["features"], index=False)

# Dashboard at feature stage is intentionally raw-feature-only. M5-002 overwrites
# it with features + signals + quality columns.
dashboard = features.copy()
dashboard.to_csv(PATHS["dashboard"], index=False)

print("Saved features:", PATHS["features"])
print("Saved dashboard:", PATHS["dashboard"])
