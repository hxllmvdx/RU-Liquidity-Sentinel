# %%
"""
M3-001: OFZ auction EDA + daily feature engineering.

Goal:
    Convert sparse OFZ auction events into a daily feature panel.

Input:
    ../../data/processed/ofz_auction_results.csv
    fallback: /mnt/data/ofz_auction_results.csv

Outputs:
    ../../data/processed/ofz_auction_event_features.csv
    ../../data/processed/ofz_auction_features_daily.csv
    backward-compatible copy:
    ../../data/processed/ofz_auction_features.csv

Design notes:
    - Event-level rows are kept in ofz_auction_event_features.csv.
    - Daily-level rows are saved in ofz_auction_features_daily.csv and also copied
      to ofz_auction_features.csv so M3-002 can consume the daily panel directly.
    - Days without auctions are not dropped. They receive has_auction = 0.
    - Event-only amounts are set to 0 on non-auction days.
    - Last known market/auction indicators are forward-filled with explicit
      staleness counters, so a downstream model can distinguish fresh data from
      stale carried information.
"""

from __future__ import annotations

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
EVENT_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_event_features.csv"
DAILY_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_features_daily.csv"
OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_features.csv"  # compatibility path

# Fallback for running this file outside the project, for example in /mnt/data.
if not INPUT_PATH.exists():
    INPUT_PATH = Path("/mnt/data/ofz_auction_results.csv")
    EVENT_OUTPUT_PATH = Path("/mnt/data/ofz_auction_event_features.csv")
    DAILY_OUTPUT_PATH = Path("/mnt/data/ofz_auction_features_daily.csv")
    OUTPUT_PATH = Path("/mnt/data/ofz_auction_features.csv")

COVER_RATIO_CLIP_UPPER = 10.0
STRESS_THRESHOLD = 0.60
ROLLING_MAD_WINDOW_DAYS = 365 * 3
MAX_FFILL_STALENESS_DAYS = 45

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
    """Robust z-score based on MAD: Median Absolute Deviation."""
    series = pd.to_numeric(series, errors="coerce")
    median = series.median(skipna=True)
    mad = (series - median).abs().median(skipna=True)

    if mad == 0 or pd.isna(mad):
        return pd.Series(0.0, index=series.index)

    return 0.6745 * (series - median) / mad


def rolling_mad_score(series: pd.Series, window: int, min_periods: int = 20) -> pd.Series:
    """Lagged rolling MAD score. shift(1) prevents current-day leakage."""
    values = pd.to_numeric(series, errors="coerce")
    hist = values.shift(1)
    median = hist.rolling(window=window, min_periods=min_periods).median()

    def _mad(x: np.ndarray) -> float:
        x = x[~np.isnan(x)]
        if len(x) == 0:
            return np.nan
        med = np.median(x)
        return np.median(np.abs(x - med))

    mad = hist.rolling(window=window, min_periods=min_periods).apply(_mad, raw=True)
    score = 0.6745 * (values - median) / mad.replace(0, np.nan)
    return score.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def weighted_mean(value: pd.Series, weight: pd.Series) -> float:
    value = pd.to_numeric(value, errors="coerce")
    weight = pd.to_numeric(weight, errors="coerce")
    mask = value.notna() & weight.notna() & (weight > 0)
    if not mask.any():
        return np.nan
    return float(np.average(value[mask], weights=weight[mask]))


def add_base_event_features(df: pd.DataFrame) -> pd.DataFrame:
    """Clean base columns and add event-level auction features."""
    df = df.copy()

    df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce").dt.normalize()
    df["ofz_issue"] = df["ofz_issue"].astype(str).str.strip()

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["auction_date"])
    df = df.sort_values(["auction_date", "ofz_issue"]).reset_index(drop=True)
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

    shifted_cover = df["cover_ratio_clipped"].shift(1)
    df["cover_ratio_roll5_mean"] = shifted_cover.rolling(window=5, min_periods=1).mean()
    df["cover_ratio_roll5_median"] = shifted_cover.rolling(window=5, min_periods=1).median()
    df["cover_ratio_roll5_std"] = shifted_cover.rolling(window=5, min_periods=2).std()

    df["MAD_score_cover"] = rolling_mad_score(
        df["cover_ratio_clipped"],
        window=min(ROLLING_MAD_WINDOW_DAYS, max(60, len(df))),
        min_periods=min(30, max(5, len(df) // 10)),
    )

    if df["yield_curve_spread_bp"].notna().sum() >= 30:
        df["MAD_score_yield_spread"] = rolling_mad_score(
            df["yield_curve_spread_bp"],
            window=min(ROLLING_MAD_WINDOW_DAYS, max(60, len(df))),
            min_periods=30,
        )
    else:
        df["MAD_score_yield_spread"] = np.nan

    return df


def build_daily_panel(event_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate auction events to one row per calendar day and fill non-auction days."""
    df = event_df.copy()

    def _agg_day(group: pd.DataFrame) -> pd.Series:
        offer = group["offer_volume_bln_rub"].sum(min_count=1)
        demand = group["demand_volume_bln_rub"].sum(min_count=1)
        placement = group["placement_volume_bln_rub"].sum(min_count=1)

        return pd.Series(
            {
                "has_auction": 1,
                "auctions_count": len(group),
                "ofz_issues": ";".join(sorted(group["ofz_issue"].dropna().astype(str).unique())),
                "offer_volume_bln_rub": offer,
                "demand_volume_bln_rub": demand,
                "placement_volume_bln_rub": placement,
                "cover_ratio": demand / offer if pd.notna(offer) and offer != 0 else np.nan,
                "weighted_avg_yield": weighted_mean(
                    group["weighted_avg_yield"], group["placement_volume_bln_rub"]
                ),
                "yield_curve_spread_bp": weighted_mean(
                    group["yield_curve_spread_bp"], group["placement_volume_bln_rub"]
                ),
                "min_event_cover_ratio": group["cover_ratio"].min(skipna=True),
                "max_event_cover_ratio": group["cover_ratio"].max(skipna=True),
                "mean_event_cover_ratio": group["cover_ratio"].mean(skipna=True),
                "any_nedospros_event": int((group["cover_ratio"] < 1.2).any()),
                "any_perespros_event": int((group["cover_ratio"] > 2.0).any()),
                "confirmed_auctions_count": int(group.get("cbr_confirmed", pd.Series(False, index=group.index)).fillna(False).sum()),
            }
        )

    daily_events = df.groupby("auction_date", as_index=True).apply(_agg_day)

    full_index = pd.date_range(df["auction_date"].min(), df["auction_date"].max(), freq="D", name="date")
    daily = daily_events.reindex(full_index)
    daily.index.name = "date"
    daily = daily.reset_index()
    daily["auction_date"] = daily["date"]

    daily["has_auction"] = daily["has_auction"].fillna(0).astype(int)
    daily["auctions_count"] = daily["auctions_count"].fillna(0).astype(int)
    daily["confirmed_auctions_count"] = daily["confirmed_auctions_count"].fillna(0).astype(int)
    daily["ofz_issues"] = daily["ofz_issues"].fillna("")

    event_amount_cols = [
        "offer_volume_bln_rub",
        "demand_volume_bln_rub",
        "placement_volume_bln_rub",
    ]
    daily.loc[daily["has_auction"].eq(0), event_amount_cols] = 0.0

    # Ratios for actual auction days.
    daily["cover_ratio"] = safe_divide(
        daily["demand_volume_bln_rub"], daily["offer_volume_bln_rub"]
    )
    daily["cover_ratio_clipped"] = daily["cover_ratio"].clip(upper=COVER_RATIO_CLIP_UPPER)
    daily["placement_to_offer_ratio"] = safe_divide(
        daily["placement_volume_bln_rub"], daily["offer_volume_bln_rub"]
    )
    daily["placement_to_demand_ratio"] = safe_divide(
        daily["placement_volume_bln_rub"], daily["demand_volume_bln_rub"]
    )

    # Carry last auction information with explicit staleness features.
    signal_cols = [
        "cover_ratio",
        "cover_ratio_clipped",
        "placement_to_offer_ratio",
        "placement_to_demand_ratio",
        "weighted_avg_yield",
        "yield_curve_spread_bp",
        "min_event_cover_ratio",
        "max_event_cover_ratio",
        "mean_event_cover_ratio",
    ]
    for col in signal_cols:
        daily[f"last_{col}"] = daily[col].ffill(limit=MAX_FFILL_STALENESS_DAYS)

    daily["last_auction_date"] = daily["date"].where(daily["has_auction"].eq(1)).ffill()
    daily["days_since_last_auction"] = (daily["date"] - daily["last_auction_date"]).dt.days
    daily["days_since_last_auction"] = daily["days_since_last_auction"].fillna(9999).astype(int)
    daily["is_stale_auction_info"] = (
        daily["days_since_last_auction"] > MAX_FFILL_STALENESS_DAYS
    ).astype(int)

    # Rolling daily context. These are shifted to avoid current-day leakage.
    shifted_has_auction = daily["has_auction"].shift(1)
    shifted_offer = daily["offer_volume_bln_rub"].shift(1)
    shifted_demand = daily["demand_volume_bln_rub"].shift(1)
    shifted_placement = daily["placement_volume_bln_rub"].shift(1)
    shifted_cover = daily["cover_ratio_clipped"].shift(1)

    daily["auctions_7d_count"] = shifted_has_auction.rolling(7, min_periods=1).sum()
    daily["auctions_30d_count"] = shifted_has_auction.rolling(30, min_periods=1).sum()
    daily["offer_7d_sum_bln_rub"] = shifted_offer.rolling(7, min_periods=1).sum()
    daily["demand_7d_sum_bln_rub"] = shifted_demand.rolling(7, min_periods=1).sum()
    daily["placement_7d_sum_bln_rub"] = shifted_placement.rolling(7, min_periods=1).sum()
    daily["offer_30d_sum_bln_rub"] = shifted_offer.rolling(30, min_periods=1).sum()
    daily["demand_30d_sum_bln_rub"] = shifted_demand.rolling(30, min_periods=1).sum()
    daily["placement_30d_sum_bln_rub"] = shifted_placement.rolling(30, min_periods=1).sum()
    daily["cover_ratio_30d_mean"] = shifted_cover.rolling(30, min_periods=1).mean()
    daily["cover_ratio_90d_mean"] = shifted_cover.rolling(90, min_periods=1).mean()

    daily["MAD_score_cover"] = rolling_mad_score(
        daily["last_cover_ratio_clipped"],
        window=ROLLING_MAD_WINDOW_DAYS,
        min_periods=60,
    )
    if daily["last_yield_curve_spread_bp"].notna().sum() >= 60:
        daily["MAD_score_yield_spread"] = rolling_mad_score(
            daily["last_yield_curve_spread_bp"],
            window=ROLLING_MAD_WINDOW_DAYS,
            min_periods=60,
        )
    else:
        daily["MAD_score_yield_spread"] = np.nan

    # Calendar features.
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month
    daily["quarter"] = daily["date"].dt.quarter
    daily["day_of_week"] = daily["date"].dt.dayofweek
    daily["is_month_end"] = daily["date"].dt.is_month_end.astype(int)
    daily["is_quarter_end"] = daily["date"].dt.is_quarter_end.astype(int)

    return daily


def add_stress_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add explainable OFZ auction stress signals to event or daily rows."""
    df = df.copy()

    cover_for_signal = df["cover_ratio"] if "cover_ratio" in df.columns else df["last_cover_ratio"]
    placement_ratio = df.get("placement_to_offer_ratio", pd.Series(np.nan, index=df.index))

    df["Flag_Nedospros"] = (cover_for_signal < 1.2).fillna(False).astype(int)
    df["Flag_Perespros"] = (cover_for_signal > 2.0).fillna(False).astype(int)

    # On non-auction days these event flags must not fire.
    if "has_auction" in df.columns:
        no_auction = df["has_auction"].eq(0)
        df.loc[no_auction, ["Flag_Nedospros", "Flag_Perespros"]] = 0

    df["Flag_Placement_Stress"] = (
        (placement_ratio < 0.5) & (cover_for_signal < 1.5)
    ).fillna(False).astype(int)

    df["Flag_Low_Cover_MAD"] = (df["MAD_score_cover"] < -2).fillna(False).astype(int)
    df["Flag_Extreme_Oversubscription"] = (cover_for_signal > 5.0).fillna(False).astype(int)

    if "has_auction" in df.columns:
        no_auction = df["has_auction"].eq(0)
        event_flag_cols = [
            "Flag_Placement_Stress",
            "Flag_Extreme_Oversubscription",
        ]
        df.loc[no_auction, event_flag_cols] = 0

    df["weak_cover_score"] = np.select(
        condlist=[
            cover_for_signal < 1.0,
            cover_for_signal < 1.2,
            cover_for_signal < 1.5,
        ],
        choicelist=[1.0, 0.8, 0.4],
        default=0.0,
    )

    df["weak_placement_score"] = np.select(
        condlist=[
            (placement_ratio < 0.3) & (cover_for_signal < 1.5),
            (placement_ratio < 0.5) & (cover_for_signal < 1.5),
            (placement_ratio < 0.8) & (cover_for_signal < 1.2),
        ],
        choicelist=[1.0, 0.7, 0.4],
        default=0.0,
    )

    df["mad_cover_score"] = np.select(
        condlist=[
            df["MAD_score_cover"] < -3,
            df["MAD_score_cover"] < -2,
            df["MAD_score_cover"] < -1,
        ],
        choicelist=[1.0, 0.7, 0.3],
        default=0.0,
    )

    if "MAD_score_yield_spread" in df.columns and df["MAD_score_yield_spread"].notna().sum() > 30:
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
        df["yield_spread_score"] = 0.0

    df["Stress_Score"] = (
        0.45 * df["weak_cover_score"]
        + 0.30 * df["weak_placement_score"]
        + 0.15 * df["mad_cover_score"]
        + 0.10 * df["yield_spread_score"]
    )

    if "has_auction" in df.columns:
        # Non-auction days should keep contextual MAD state, but not become
        # auction stress events by forward-filled ratios alone.
        no_auction = df["has_auction"].eq(0)
        df.loc[no_auction, ["weak_cover_score", "weak_placement_score", "Stress_Score"]] = 0.0

    df["Stress_Flag"] = (df["Stress_Score"] >= STRESS_THRESHOLD).astype(int)
    df["Stress_Level"] = pd.cut(
        df["Stress_Score"],
        bins=[-0.01, 0.30, 0.60, 1.00],
        labels=["normal", "warning", "stress"],
    )

    return df


def print_dataset_report(df: pd.DataFrame, title: str) -> None:
    """Print compact diagnostics for notebook/script runs."""
    date_col = "date" if "date" in df.columns else "auction_date"
    print(f"\n=== {title} ===")
    print("Shape:", df.shape)
    print("Date range:", df[date_col].min(), "->", df[date_col].max())

    if "has_auction" in df.columns:
        print("Auction days:", int(df["has_auction"].sum()))
        print("Non-auction days:", int((df["has_auction"] == 0).sum()))

    print("\nMissing values, top 10:")
    print(df.isna().sum().sort_values(ascending=False).head(10))

    if "Stress_Flag" in df.columns:
        print("\nStress_Flag share:")
        print(df["Stress_Flag"].value_counts(normalize=True, dropna=False))

    signal_cols = [
        col for col in [
            "Flag_Nedospros",
            "Flag_Perespros",
            "Flag_Placement_Stress",
            "Flag_Low_Cover_MAD",
            "Flag_Extreme_Oversubscription",
        ] if col in df.columns
    ]
    if signal_cols:
        print("\nSignal reasons:")
        print(df[signal_cols].sum().sort_values(ascending=False))


def plot_daily_cover_ratio(daily: pd.DataFrame) -> None:
    plot_df = daily[daily["has_auction"].eq(1)].copy()
    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["date"], plot_df["cover_ratio_clipped"], label="Daily auction cover ratio, clipped")
    plt.axhline(1.2, linestyle="--", label="Недоспрос threshold 1.2")
    plt.axhline(2.0, linestyle="--", label="Переспрос threshold 2.0")
    plt.title("Daily OFZ auction cover ratio")
    plt.xlabel("Дата")
    plt.ylabel("Cover ratio, clipped")
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_daily_volumes(daily: pd.DataFrame) -> None:
    plt.figure(figsize=(14, 6))
    plt.plot(daily["date"], daily["offer_30d_sum_bln_rub"], label="Offer, rolling 30d")
    plt.plot(daily["date"], daily["demand_30d_sum_bln_rub"], label="Demand, rolling 30d")
    plt.plot(daily["date"], daily["placement_30d_sum_bln_rub"], label="Placement, rolling 30d")
    plt.title("OFZ auction volumes, rolling 30 days")
    plt.xlabel("Дата")
    plt.ylabel("млрд руб.")
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_daily_mad(daily: pd.DataFrame) -> None:
    plt.figure(figsize=(14, 6))
    plt.plot(daily["date"], daily["MAD_score_cover"], label="MAD-score cover")
    plt.axhline(-2, linestyle="--", label="Low cover threshold -2")
    plt.axhline(2, linestyle="--", label="High cover threshold 2")
    plt.title("Daily MAD-score by last OFZ cover ratio")
    plt.xlabel("Дата")
    plt.ylabel("MAD-score")
    plt.legend()
    plt.tight_layout()
    plt.show()


# %%
# -----------------------------------------------------------------------------
# Load + feature engineering
# -----------------------------------------------------------------------------
df_raw = pd.read_csv(INPUT_PATH)
event_df = add_base_event_features(df_raw)
event_df = add_stress_signals(event_df)

daily_df = build_daily_panel(event_df)
daily_df = add_stress_signals(daily_df)

print_dataset_report(event_df, "Event-level OFZ features")
print_dataset_report(daily_df, "Daily OFZ feature panel")

# %%
# Top stressful auction days for manual sanity check.
TOP_COLUMNS = [
    "date",
    "has_auction",
    "auctions_count",
    "ofz_issues",
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

daily_df[TOP_COLUMNS].sort_values("Stress_Score", ascending=False).head(20)

# %%
# Save processed datasets.
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
event_df.to_csv(EVENT_OUTPUT_PATH, index=False)
daily_df.to_csv(DAILY_OUTPUT_PATH, index=False)
daily_df.to_csv(OUTPUT_PATH, index=False)

print(f"Saved event features: {EVENT_OUTPUT_PATH}")
print(f"Saved daily features: {DAILY_OUTPUT_PATH}")
print(f"Saved compatibility daily features: {OUTPUT_PATH}")

# %%
# -----------------------------------------------------------------------------
# EDA plots
# -----------------------------------------------------------------------------
plot_daily_cover_ratio(daily_df)

# %%
plot_daily_volumes(daily_df)

# %%
plot_daily_mad(daily_df)

# %%
plt.figure(figsize=(10, 5))
plt.hist(daily_df.loc[daily_df["has_auction"].eq(1), "cover_ratio_clipped"].dropna(), bins=50)
plt.title("Distribution of daily OFZ cover ratio")
plt.xlabel("Cover ratio, clipped")
plt.ylabel("Auction days")
plt.tight_layout()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(daily_df["date"], daily_df["Stress_Score"], label="Daily auction Stress Score")
plt.axhline(0.3, linestyle="--", label="Warning threshold 0.3")
plt.axhline(0.6, linestyle="--", label="Stress threshold 0.6")
plt.title("Rule-based Stress Score for OFZ auction days")
plt.xlabel("Дата")
plt.ylabel("Stress Score")
plt.legend()
plt.tight_layout()
plt.show()
