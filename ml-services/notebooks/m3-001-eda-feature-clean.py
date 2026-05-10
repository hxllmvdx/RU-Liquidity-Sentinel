# %%
"""
M3-001: OFZ auction EDA + feature engineering.

Input:
    ../../data/processed/ofz_auction_results.csv

Output:
    ../../data/processed/ofz_auction_features.csv

Main outputs:
    - cover_ratio / cover_ratio_clipped
    - placement ratios
    - MAD_score_cover
    - rule-based stress flags
    - Stress_Score / Stress_Level / Stress_Flag
    - basic EDA plots
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# %%
# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
PROJECT_DATA_DIR = Path("../../data/processed")
INPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_results.csv"
OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_features.csv"

# Fallback for running this file outside the project, for example in /mnt/data.
if not INPUT_PATH.exists():
    INPUT_PATH = Path("/mnt/data/ofz_auction_results.csv")
    OUTPUT_PATH = Path("/mnt/data/ofz_auction_features.csv")

COVER_RATIO_CLIP_UPPER = 10.0
STRESS_THRESHOLD = 0.60

NUMERIC_COLS = [
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "weighted_avg_yield",
    "yield_curve_spread_bp",
]

# %%
# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide two pandas Series and return NaN for zero/missing denominator."""
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")

    result = numerator / denominator.replace(0, np.nan)
    return result.replace([np.inf, -np.inf], np.nan)


def mad_score(series: pd.Series) -> pd.Series:
    """
    Robust z-score based on MAD: Median Absolute Deviation.

    Positive value means above median, negative value means below median.
    """
    series = pd.to_numeric(series, errors="coerce")
    median = series.median(skipna=True)
    mad = (series - median).abs().median(skipna=True)

    if mad == 0 or pd.isna(mad):
        return pd.Series(0.0, index=series.index)

    return 0.6745 * (series - median) / mad


def add_base_features(df: pd.DataFrame) -> pd.DataFrame:
    """Clean base columns and add core auction features."""
    df = df.copy()

    df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce")
    df["ofz_issue"] = df["ofz_issue"].astype(str).str.strip()

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("auction_date").reset_index(drop=True)
    df = df.drop_duplicates(subset=["auction_date", "ofz_issue"], keep="last")
    df = df.reset_index(drop=True)

    # Recalculate ratios from raw volumes to avoid parser/rounding inconsistencies.
    df["cover_ratio"] = safe_divide(
        df["demand_volume_bln_rub"],
        df["offer_volume_bln_rub"],
    )
    df["cover_ratio_clipped"] = df["cover_ratio"].clip(upper=COVER_RATIO_CLIP_UPPER)

    df["placement_to_offer_ratio"] = safe_divide(
        df["placement_volume_bln_rub"],
        df["offer_volume_bln_rub"],
    )
    df["placement_to_demand_ratio"] = safe_divide(
        df["placement_volume_bln_rub"],
        df["demand_volume_bln_rub"],
    )

    # Calendar features.
    df["year"] = df["auction_date"].dt.year
    df["month"] = df["auction_date"].dt.month
    df["quarter"] = df["auction_date"].dt.quarter
    df["day_of_week"] = df["auction_date"].dt.dayofweek

    # OFZ issue features.
    df["ofz_prefix"] = df["ofz_issue"].str[:2]
    df["ofz_series"] = df["ofz_issue"].str[:5]

    # Lagged rolling features. shift(1) prevents current-row leakage.
    shifted_cover = df["cover_ratio_clipped"].shift(1)
    df["cover_ratio_roll5_mean"] = shifted_cover.rolling(window=5, min_periods=1).mean()
    df["cover_ratio_roll5_median"] = shifted_cover.rolling(window=5, min_periods=1).median()
    df["cover_ratio_roll5_std"] = shifted_cover.rolling(window=5, min_periods=2).std()

    df["MAD_score_cover"] = mad_score(df["cover_ratio_clipped"])

    return df


def add_stress_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add explainable auction stress signals.

    Stress_Flag is intentionally derived from Stress_Score, not from a wide OR rule.
    This avoids marking half of the dataset as stress just because one weak condition fired.
    """
    df = df.copy()

    # Raw rule flags from task requirements.
    df["Flag_Nedospros"] = (df["cover_ratio"] < 1.2).astype(int)
    df["Flag_Perespros"] = (df["cover_ratio"] > 2.0).astype(int)

    # Additional explainable flags.
    df["Flag_Placement_Stress"] = (
        (df["placement_to_offer_ratio"] < 0.5)
        & (df["cover_ratio"] < 1.5)
    ).astype(int)

    df["Flag_Low_Cover_MAD"] = (df["MAD_score_cover"] < -2).astype(int)
    df["Flag_Extreme_Oversubscription"] = (df["cover_ratio"] > 5.0).astype(int)

    # Score 1: weak demand.
    df["weak_cover_score"] = np.select(
        condlist=[
            df["cover_ratio"] < 1.0,
            df["cover_ratio"] < 1.2,
            df["cover_ratio"] < 1.5,
        ],
        choicelist=[1.0, 0.8, 0.4],
        default=0.0,
    )

    # Score 2: weak placement, but only when demand is not strong enough.
    df["weak_placement_score"] = np.select(
        condlist=[
            (df["placement_to_offer_ratio"] < 0.3) & (df["cover_ratio"] < 1.5),
            (df["placement_to_offer_ratio"] < 0.5) & (df["cover_ratio"] < 1.5),
            (df["placement_to_offer_ratio"] < 0.8) & (df["cover_ratio"] < 1.2),
        ],
        choicelist=[1.0, 0.7, 0.4],
        default=0.0,
    )

    # Score 3: statistically low cover ratio.
    df["mad_cover_score"] = np.select(
        condlist=[
            df["MAD_score_cover"] < -3,
            df["MAD_score_cover"] < -2,
            df["MAD_score_cover"] < -1,
        ],
        choicelist=[1.0, 0.7, 0.3],
        default=0.0,
    )

    # Yield spread is currently a dataset gap. Keep a forward-compatible hook.
    if (
        "yield_curve_spread_bp" in df.columns
        and df["yield_curve_spread_bp"].notna().sum() > 30
    ):
        df["MAD_score_yield_spread"] = mad_score(df["yield_curve_spread_bp"])
        df["yield_spread_score"] = np.select(
            condlist=[
                df["MAD_score_yield_spread"] > 3,
                df["MAD_score_yield_spread"] > 2,
                df["MAD_score_yield_spread"] > 1,
            ],
            choicelist=[1.0, 0.7, 0.3],
            default=0.0,
        )
    else:
        df["MAD_score_yield_spread"] = np.nan
        df["yield_spread_score"] = 0.0

    # Final explainable stress score.
    # Current MVP mostly relies on demand/placement because yield spread is missing.
    df["Stress_Score"] = (
        0.45 * df["weak_cover_score"]
        + 0.30 * df["weak_placement_score"]
        + 0.15 * df["mad_cover_score"]
        + 0.10 * df["yield_spread_score"]
    )

    df["Stress_Flag"] = (df["Stress_Score"] >= STRESS_THRESHOLD).astype(int)

    df["Stress_Level"] = pd.cut(
        df["Stress_Score"],
        bins=[-0.01, 0.30, 0.60, 1.00],
        labels=["normal", "warning", "stress"],
    )

    return df


def print_dataset_report(df: pd.DataFrame) -> None:
    """Print compact diagnostics for notebook/script runs."""
    print("Shape:", df.shape)
    print("\nDate range:")
    print(df["auction_date"].min(), "->", df["auction_date"].max())

    print("\nMissing values, top 10:")
    print(df.isna().sum().sort_values(ascending=False).head(10))

    print("\nStress_Flag share:")
    print(df["Stress_Flag"].value_counts(normalize=True, dropna=False))

    print("\nStress_Level counts:")
    print(df["Stress_Level"].value_counts(dropna=False))

    print("\nSignal reasons:")
    signal_cols = [
        "Flag_Nedospros",
        "Flag_Perespros",
        "Flag_Placement_Stress",
        "Flag_Low_Cover_MAD",
        "Flag_Extreme_Oversubscription",
    ]
    print(df[signal_cols].sum().sort_values(ascending=False))


# %%
# -----------------------------------------------------------------------------
# Load + feature engineering
# -----------------------------------------------------------------------------
df_raw = pd.read_csv(INPUT_PATH)
df = add_base_features(df_raw)
df = add_stress_signals(df)

print_dataset_report(df)

# %%
# Top stressful rows for manual sanity check.
TOP_COLUMNS = [
    "auction_date",
    "ofz_issue",
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "cover_ratio_clipped",
    "placement_to_offer_ratio",
    "MAD_score_cover",
    "Flag_Nedospros",
    "Flag_Placement_Stress",
    "Stress_Score",
    "Stress_Level",
    "Stress_Flag",
]

df[TOP_COLUMNS].sort_values("Stress_Score", ascending=False).head(20)

# %%
# Save processed dataset.
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)
print(f"Saved: {OUTPUT_PATH}")

# %%
# -----------------------------------------------------------------------------
# EDA plots
# -----------------------------------------------------------------------------
plt.figure(figsize=(14, 6))
plt.plot(df["auction_date"], df["cover_ratio_clipped"], label="Cover ratio clipped")
plt.axhline(1.2, linestyle="--", label="Недоспрос threshold 1.2")
plt.axhline(2.0, linestyle="--", label="Переспрос threshold 2.0")
plt.title("Cover ratio ОФЗ по времени")
plt.xlabel("Дата")
plt.ylabel("Cover ratio, clipped")
plt.legend()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["auction_date"], df["offer_volume_bln_rub"], label="Offer")
plt.plot(df["auction_date"], df["demand_volume_bln_rub"], label="Demand")
plt.plot(df["auction_date"], df["placement_volume_bln_rub"], label="Placement")
plt.title("Объёмы ОФЗ-аукционов")
plt.xlabel("Дата")
plt.ylabel("млрд руб.")
plt.legend()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["auction_date"], df["MAD_score_cover"], label="MAD-score cover")
plt.axhline(-2, linestyle="--", label="Low cover threshold -2")
plt.axhline(2, linestyle="--", label="High cover threshold 2")
plt.title("MAD-score по Cover ratio")
plt.xlabel("Дата")
plt.ylabel("MAD-score")
plt.legend()
plt.show()

# %%
plt.figure(figsize=(10, 5))
plt.hist(df["cover_ratio_clipped"].dropna(), bins=50)
plt.title("Распределение Cover ratio")
plt.xlabel("Cover ratio, clipped")
plt.ylabel("Количество")
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["auction_date"], df["Stress_Score"], label="Stress Score")
plt.axhline(0.3, linestyle="--", label="Warning threshold 0.3")
plt.axhline(0.6, linestyle="--", label="Stress threshold 0.6")
plt.title("Rule-based Stress Score ОФЗ-аукционов")
plt.xlabel("Дата")
plt.ylabel("Stress Score")
plt.legend()
plt.show()
