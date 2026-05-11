# %% [markdown]
# # M2 — Repo Auctions: EDA + Daily Feature Panel
#
# One row = one calendar day from the earliest auction date to the latest auction date.
# Days without auctions are kept in the table and auction-related numeric cells are filled with 0.
# Auction volume is used only for same-day volume-weighted aggregation.
# No hard term coefficient is used.

# %%
from __future__ import annotations

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)

# %%
# Config
RAW_INPUT_PATH = Path("../data/raw/cbr/repo/cbr_repo_2002-11-21_2026-05-05.csv")
PROCESSED_DIR = Path("../data/processed")
FEATURES_OUTPUT_PATH = PROCESSED_DIR / "repo_module_daily_features.csv"
EVENTS_OUTPUT_PATH = PROCESSED_DIR / "repo_module_event_features.csv"

# Fallbacks for direct sandbox checks.
for candidate in [
    Path("../../data/raw/cbr/repo/cbr_repo_2002-11-21_2026-05-05.csv"),
    Path("/mnt/data/cbr_repo_2002-11-21_2026-05-05.csv"),
]:
    if not RAW_INPUT_PATH.exists() and candidate.exists():
        RAW_INPUT_PATH = candidate
        PROCESSED_DIR = (
            candidate.parents[3] / "processed"
            if "raw" in candidate.parts
            else Path("/mnt/data")
        )
        FEATURES_OUTPUT_PATH = PROCESSED_DIR / "repo_module_daily_features.csv"
        EVENTS_OUTPUT_PATH = PROCESSED_DIR / "repo_module_event_features.csv"

MAIN_TERM_DAYS = 7
DEMAND_THRESHOLD = 2.0

# %%
# Column normalization helpers
COLUMN_ALIASES = {
    "date": "auction_date",
    "дата": "auction_date",
    "auction_date": "auction_date",
    "operation_date": "auction_date",
    "auction_dt": "auction_date",
    "срок": "term_days",
    "term": "term_days",
    "term_days": "term_days",
    "tenor_days": "term_days",
    "объем спроса": "demand_volume_bln_rub",
    "объём спроса": "demand_volume_bln_rub",
    "demand": "demand_volume_bln_rub",
    "demand_amount": "demand_volume_bln_rub",
    "demand_amount_bln_rub": "demand_volume_bln_rub",
    "demand_volume_bln_rub": "demand_volume_bln_rub",
    "объем размещения": "placement_volume_bln_rub",
    "объём размещения": "placement_volume_bln_rub",
    "placement": "placement_volume_bln_rub",
    "placed_amount": "placement_volume_bln_rub",
    "placement_amount": "placement_volume_bln_rub",
    "placed_amount_bln_rub": "placement_volume_bln_rub",
    "placement_amount_bln_rub": "placement_volume_bln_rub",
    "placement_volume_bln_rub": "placement_volume_bln_rub",
    "ставка отсечения": "cutoff_rate_percent",
    "cut_off_rate": "cutoff_rate_percent",
    "cutoff_rate": "cutoff_rate_percent",
    "cut_off_rate_percent": "cutoff_rate_percent",
    "cutoff_rate_percent": "cutoff_rate_percent",
    "средневзвешенная ставка": "weighted_average_rate_percent",
    "weighted_avg_rate": "weighted_average_rate_percent",
    "weighted_average_rate": "weighted_average_rate_percent",
    "weighted_average_rate_percent": "weighted_average_rate_percent",
    "ключевая ставка": "key_rate_percent",
    "key_rate": "key_rate_percent",
    "key_rate_percent": "key_rate_percent",
    "rate_spread": "rate_spread_to_key_rate_percent",
    "rate_spread_percent": "rate_spread_to_key_rate_percent",
    "rate_spread_to_key_rate_percent": "rate_spread_to_key_rate_percent",
}


def _norm_col_name(name: str) -> str:
    s = str(name).strip().lower().replace("ё", "е")
    s = re.sub(r"[\n\r\t]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace("/", "_").replace("-", "_")
    return s


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for col in df.columns:
        norm = _norm_col_name(col)
        canonical = COLUMN_ALIASES.get(norm)
        if canonical is None:
            compact = norm.replace(" ", "_")
            canonical = COLUMN_ALIASES.get(compact, compact)
        mapping[col] = canonical
    out = df.rename(columns=mapping).copy()
    out = out.loc[:, ~out.columns.duplicated()].copy()
    return out


def parse_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    s = series.astype(str)
    s = s.str.replace("\u00a0", " ", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.replace(",", ".", regex=False)
    s = s.str.replace("%", "", regex=False)
    s = s.str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    mask = v.notna() & w.notna() & (w > 0)
    if not mask.any():
        return 0.0
    return float(np.average(v[mask], weights=w[mask]))


# %%
# Load raw data
if not RAW_INPUT_PATH.exists():
    raise FileNotFoundError(
        f"Raw repo CSV not found: {RAW_INPUT_PATH}. Expected path from project root: "
        "../data/raw/cbr/repo/cbr_repo_2002-11-21_2026-05-05.csv"
    )

raw = pd.read_csv(RAW_INPUT_PATH)
print("Raw path:", RAW_INPUT_PATH)
print("Raw shape:", raw.shape)
print("Raw columns:", list(raw.columns))

# %%
# Clean event-level data
events = normalize_columns(raw)

if "auction_date" not in events.columns:
    raise ValueError(
        f"Could not find auction date column. Columns after normalization: {list(events.columns)}"
    )

events["auction_date"] = pd.to_datetime(
    events["auction_date"], errors="coerce"
).dt.normalize()
events = events.dropna(subset=["auction_date"]).copy()

for col in [
    "term_days",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cutoff_rate_percent",
    "weighted_average_rate_percent",
    "key_rate_percent",
    "rate_spread_to_key_rate_percent",
]:
    if col in events.columns:
        events[col] = parse_numeric(events[col])
    else:
        events[col] = np.nan

# Volumes are required for weighting; missing values become 0.
events["demand_volume_bln_rub"] = (
    events["demand_volume_bln_rub"].fillna(0.0).clip(lower=0.0)
)
events["placement_volume_bln_rub"] = (
    events["placement_volume_bln_rub"].fillna(0.0).clip(lower=0.0)
)

# Auction volume weight: prefer actual placement, fallback to demand.
events["auction_volume_bln_rub"] = events["placement_volume_bln_rub"].where(
    events["placement_volume_bln_rub"] > 0, events["demand_volume_bln_rub"]
)
events["auction_volume_bln_rub"] = (
    events["auction_volume_bln_rub"].fillna(0.0).clip(lower=0.0)
)

# Feature calculations.
events["cover_ratio"] = np.where(
    events["placement_volume_bln_rub"] > 0,
    events["demand_volume_bln_rub"] / events["placement_volume_bln_rub"],
    np.nan,
)

if events["rate_spread_to_key_rate_percent"].isna().all():
    events["rate_spread_to_key_rate_percent"] = (
        events["cutoff_rate_percent"] - events["key_rate_percent"]
    )

events["is_7d_repo"] = events["term_days"].eq(MAIN_TERM_DAYS).fillna(False)
events["Flag_Demand_event"] = (
    events["cover_ratio"].gt(DEMAND_THRESHOLD).fillna(False)
)

events = events.sort_values(["auction_date", "term_days"]).reset_index(
    drop=True
)

print("Clean events shape:", events.shape)
print(
    "Date range:",
    events["auction_date"].min(),
    "->",
    events["auction_date"].max(),
)
print("7d auction share:", round(float(events["is_7d_repo"].mean()), 3))

# %%
# Data quality diagnostics
required_cols = [
    "auction_date",
    "term_days",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "auction_volume_bln_rub",
    "cover_ratio",
    "rate_spread_to_key_rate_percent",
]
print("\nMissing values share:")
print(events[required_cols].isna().mean().sort_values(ascending=False))
print(
    "\nRows with positive volume:",
    int((events["auction_volume_bln_rub"] > 0).sum()),
)
print("Rows with Flag_Demand_event:", int(events["Flag_Demand_event"].sum()))

# %%
# Daily aggregation helpers


def aggregate_daily_group(g: pd.DataFrame) -> pd.Series:
    total_demand = float(g["demand_volume_bln_rub"].sum())
    total_placement = float(g["placement_volume_bln_rub"].sum())
    total_volume = float(g["auction_volume_bln_rub"].sum())

    seven = g[g["is_7d_repo"]].copy()
    repo_7d_demand = (
        float(seven["demand_volume_bln_rub"].sum()) if len(seven) else 0.0
    )
    repo_7d_placement = (
        float(seven["placement_volume_bln_rub"].sum()) if len(seven) else 0.0
    )
    repo_7d_volume = (
        float(seven["auction_volume_bln_rub"].sum()) if len(seven) else 0.0
    )

    return pd.Series(
        {
            "has_auction": 1,
            "auction_count": int(len(g)),
            "total_demand_volume_bln_rub": total_demand,
            "total_placement_volume_bln_rub": total_placement,
            "total_auction_volume_bln_rub": total_volume,
            "cover_ratio_volume_weighted": weighted_average(
                g["cover_ratio"], g["auction_volume_bln_rub"]
            ),
            "rate_spread_volume_weighted": weighted_average(
                g["rate_spread_to_key_rate_percent"],
                g["auction_volume_bln_rub"],
            ),
            "cutoff_rate_volume_weighted": weighted_average(
                g["cutoff_rate_percent"], g["auction_volume_bln_rub"]
            ),
            "weighted_avg_rate_volume_weighted": weighted_average(
                g["weighted_average_rate_percent"], g["auction_volume_bln_rub"]
            ),
            "has_7d_repo": int(len(seven) > 0),
            "repo_7d_auction_count": int(len(seven)),
            "repo_7d_demand_volume_bln_rub": repo_7d_demand,
            "repo_7d_placement_volume_bln_rub": repo_7d_placement,
            "repo_7d_auction_volume_bln_rub": repo_7d_volume,
            "repo_7d_cover_ratio": weighted_average(
                seven["cover_ratio"], seven["auction_volume_bln_rub"]
            ),
            "repo_7d_rate_spread": weighted_average(
                seven["rate_spread_to_key_rate_percent"],
                seven["auction_volume_bln_rub"],
            ),
            "repo_7d_volume_share": repo_7d_volume / total_volume
            if total_volume > 0
            else 0.0,
            "Flag_Demand": bool(g["Flag_Demand_event"].any()),
        }
    )


# %%
# Build complete daily panel
min_date = events["auction_date"].min()
max_date = events["auction_date"].max()
all_days = pd.DataFrame({"date": pd.date_range(min_date, max_date, freq="D")})

daily_auction = events.groupby("auction_date", as_index=False).apply(
    aggregate_daily_group
)
# pandas can place the group key in a column named auction_date or level; normalize it.
if isinstance(daily_auction.index, pd.MultiIndex):
    daily_auction = daily_auction.reset_index(drop=True)
if "auction_date" in daily_auction.columns:
    daily_auction = daily_auction.rename(columns={"auction_date": "date"})
else:
    daily_auction = daily_auction.reset_index().rename(
        columns={"auction_date": "date"}
    )

daily = all_days.merge(daily_auction, on="date", how="left")

numeric_cols = [c for c in daily.columns if c != "date" and c != "Flag_Demand"]
for col in numeric_cols:
    daily[col] = pd.to_numeric(daily[col], errors="coerce").fillna(0.0)

daily["has_auction"] = daily["has_auction"].astype(int)
daily["has_7d_repo"] = daily["has_7d_repo"].astype(int)
daily["auction_count"] = daily["auction_count"].astype(int)
daily["repo_7d_auction_count"] = daily["repo_7d_auction_count"].astype(int)
daily["Flag_Demand"] = daily["Flag_Demand"].fillna(False).astype(bool)

# For no-auction days all auction-related values are explicitly neutral zero/false.
no_auction = daily["has_auction"].eq(0)

bool_cols = daily.select_dtypes(include=["bool"]).columns.tolist()
numeric_cols = daily.select_dtypes(include=["number"]).columns.tolist()
object_cols = daily.select_dtypes(include=["object", "string"]).columns.tolist()

bool_cols = [c for c in bool_cols if c != "date"]
numeric_cols = [c for c in numeric_cols if c != "date"]
object_cols = [c for c in object_cols if c != "date"]

daily.loc[no_auction, numeric_cols] = 0
daily.loc[no_auction, bool_cols] = False
daily.loc[no_auction, object_cols] = ""

flag_cols = ["has_auction", "has_7d_repo", "Flag_Demand"]

for col in flag_cols:
    if col in daily.columns:
        daily[col] = daily[col].fillna(False).astype(bool)

print("Daily panel shape:", daily.shape)
print("Daily date range:", daily["date"].min(), "->", daily["date"].max())
print("Calendar days:", len(daily))
print("Auction days:", int(daily["has_auction"].sum()))
print("No-auction days:", int((daily["has_auction"] == 0).sum()))

print("Daily panel shape:", daily.shape)
print("Daily date range:", daily["date"].min(), "->", daily["date"].max())
print("Calendar days:", len(daily))
print("Auction days:", int(daily["has_auction"].sum()))
print("No-auction days:", int((daily["has_auction"] == 0).sum()))

# %%
# Sanity checks: no-auction days must be zero-filled
check_cols = [c for c in daily.columns if c != "date"]
no_auction_non_zero = (
    daily.loc[daily["has_auction"].eq(0), check_cols]
    .select_dtypes(include=["number"])
    .abs()
    .sum(axis=1)
    != 0
).sum()
print("No-auction rows with non-zero numeric cells:", int(no_auction_non_zero))
if no_auction_non_zero:
    raise AssertionError(
        "No-auction days must have zero auction-related numeric cells"
    )

# %%
# Export outputs
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
events.to_csv(EVENTS_OUTPUT_PATH, index=False)
daily.to_csv(FEATURES_OUTPUT_PATH, index=False)
print("Saved event features:", EVENTS_OUTPUT_PATH)
print("Saved daily features:", FEATURES_OUTPUT_PATH)
print("Daily feature columns:")
print(list(daily.columns))
