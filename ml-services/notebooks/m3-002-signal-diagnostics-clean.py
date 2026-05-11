# %%
"""
M3-002: OFZ daily signal diagnostics and dashboard export.

This file consumes the daily M3 feature panel from M3-001.

Input priority:
    ../../data/processed/ofz_auction_features_daily.csv
    ../../data/processed/ofz_auction_features.csv
    fallback: /mnt/data/ofz_auction_features_daily.csv
    fallback: /mnt/data/ofz_auction_features.csv

Outputs:
    ../../data/processed/ofz_auction_signals_daily.csv
    ../../data/processed/ofz_auction_signals.csv       # compatibility copy
    ../../data/processed/ofz_m3_signal_summary.csv
    ../../data/processed/ofz_cover_ratio_dashboard.png
    ../../data/processed/ofz_yield_spread_dashboard.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

# %%
# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
PROJECT_DATA_DIR = Path("../../data/processed")
FEATURES_DAILY_PATH = PROJECT_DATA_DIR / "ofz_auction_features_daily.csv"
FEATURES_PATH = PROJECT_DATA_DIR / "ofz_auction_features.csv"
SIGNALS_DAILY_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_signals_daily.csv"
SIGNALS_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_signals.csv"
SUMMARY_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_m3_signal_summary.csv"
COVER_CHART_PATH = PROJECT_DATA_DIR / "ofz_cover_ratio_dashboard.png"
SPREAD_CHART_PATH = PROJECT_DATA_DIR / "ofz_yield_spread_dashboard.png"

if not FEATURES_DAILY_PATH.exists() and not FEATURES_PATH.exists():
    FEATURES_DAILY_PATH = Path("/mnt/data/ofz_auction_features_daily.csv")
    FEATURES_PATH = Path("/mnt/data/ofz_auction_features.csv")
    SIGNALS_DAILY_OUTPUT_PATH = Path("/mnt/data/ofz_auction_signals_daily.csv")
    SIGNALS_OUTPUT_PATH = Path("/mnt/data/ofz_auction_signals.csv")
    SUMMARY_OUTPUT_PATH = Path("/mnt/data/ofz_m3_signal_summary.csv")
    COVER_CHART_PATH = Path("/mnt/data/ofz_cover_ratio_dashboard.png")
    SPREAD_CHART_PATH = Path("/mnt/data/ofz_yield_spread_dashboard.png")

COVER_NEDOSPROS_THRESHOLD = 1.2
COVER_PERESPROS_THRESHOLD = 2.0
MAD_ALERT_ABS_THRESHOLD = 2.0
STALE_INFO_THRESHOLD_DAYS = 45

REQUIRED_COLS = [
    "date",
    "auction_date",
    "has_auction",
    "auctions_count",
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "cover_ratio_clipped",
    "last_cover_ratio",
    "last_cover_ratio_clipped",
    "days_since_last_auction",
    "MAD_score_cover",
    "MAD_score_yield_spread",
    "Flag_Nedospros",
    "Flag_Perespros",
]

DASHBOARD_COLS = [
    "date",
    "auction_date",
    "has_auction",
    "auctions_count",
    "ofz_issues",
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "cover_ratio_clipped",
    "last_cover_ratio",
    "last_cover_ratio_clipped",
    "weighted_avg_yield",
    "last_weighted_avg_yield",
    "yield_curve_spread_bp",
    "last_yield_curve_spread_bp",
    "days_since_last_auction",
    "is_stale_auction_info",
    "auctions_7d_count",
    "auctions_30d_count",
    "offer_30d_sum_bln_rub",
    "demand_30d_sum_bln_rub",
    "placement_30d_sum_bln_rub",
    "cover_ratio_30d_mean",
    "cover_ratio_90d_mean",
    "MAD_score_cover",
    "MAD_score_yield_spread",
    "Flag_Nedospros",
    "Flag_Perespros",
    "Signal_Cover_MAD_Alert",
    "Signal_YieldSpread_MAD_Alert",
    "Auction_State",
    "Daily_Signal_State",
    "Stress_Score",
    "Stress_Level",
    "Stress_Flag",
]

# %%
# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def resolve_features_path() -> Path:
    for path in [FEATURES_DAILY_PATH, FEATURES_PATH]:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Feature file not found. Checked: {FEATURES_DAILY_PATH}, {FEATURES_PATH}"
    )


def load_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    if "date" not in df.columns and "auction_date" in df.columns:
        # Backward-compatible handling for old event-level file. It is better to
        # regenerate M3-001, but this keeps diagnostics from crashing.
        df["date"] = df["auction_date"]
        df["has_auction"] = 1
        df["auctions_count"] = 1
        df["last_cover_ratio"] = df.get("cover_ratio")
        df["last_cover_ratio_clipped"] = df.get("cover_ratio_clipped")
        df["days_since_last_auction"] = 0
        df["is_stale_auction_info"] = 0

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce").dt.normalize()
    df = df.sort_values("date").reset_index(drop=True)
    if "ofz_issues" in df.columns:
        df["ofz_issues"] = df["ofz_issues"].fillna("").astype(str)

    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_cols = [
        "has_auction",
        "auctions_count",
        "offer_volume_bln_rub",
        "demand_volume_bln_rub",
        "placement_volume_bln_rub",
        "cover_ratio",
        "cover_ratio_clipped",
        "last_cover_ratio",
        "last_cover_ratio_clipped",
        "weighted_avg_yield",
        "last_weighted_avg_yield",
        "yield_curve_spread_bp",
        "last_yield_curve_spread_bp",
        "days_since_last_auction",
        "is_stale_auction_info",
        "MAD_score_cover",
        "MAD_score_yield_spread",
        "Stress_Score",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["has_auction", "Flag_Nedospros", "Flag_Perespros"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    if "is_stale_auction_info" not in df.columns:
        df["is_stale_auction_info"] = (
            df["days_since_last_auction"] > STALE_INFO_THRESHOLD_DAYS
        ).astype(int)

    return df


def add_dashboard_states(df: pd.DataFrame) -> pd.DataFrame:
    """Add non-ML alert columns for the dashboard/aggregation layer."""
    df = df.copy()

    df["Signal_Cover_MAD_Alert"] = (
        df["MAD_score_cover"].abs() >= MAD_ALERT_ABS_THRESHOLD
    ).fillna(False).astype(int)

    df["Signal_YieldSpread_MAD_Alert"] = (
        df["MAD_score_yield_spread"].abs() >= MAD_ALERT_ABS_THRESHOLD
    ).fillna(False).astype(int)

    # Event state is only meaningful on auction days.
    df["Auction_State"] = np.select(
        condlist=[
            (df["has_auction"] == 0),
            (df["Flag_Nedospros"] == 1),
            (df["Flag_Perespros"] == 1),
        ],
        choicelist=["no_auction", "nedospros", "perespros"],
        default="neutral",
    )

    # Daily signal state can carry statistical alerts even on non-auction days,
    # but it is explicitly marked as stale when last auction data is too old.
    df["Daily_Signal_State"] = np.select(
        condlist=[
            df["Auction_State"].eq("nedospros"),
            df["Auction_State"].eq("perespros"),
            df["is_stale_auction_info"].eq(1),
            df["Signal_Cover_MAD_Alert"].eq(1),
            df["Signal_YieldSpread_MAD_Alert"].eq(1),
        ],
        choicelist=[
            "auction_nedospros",
            "auction_perespros",
            "stale_no_recent_auction",
            "cover_mad_alert",
            "yield_spread_mad_alert",
        ],
        default="neutral",
    )

    return df


def build_year_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily signals by year for quick reporting."""
    summary = (
        df.assign(year=df["date"].dt.year)
        .groupby("year", dropna=False)
        .agg(
            calendar_days=("date", "count"),
            auction_days=("has_auction", "sum"),
            auctions_total=("auctions_count", "sum"),
            avg_cover_ratio_on_auction_days=("cover_ratio", "mean"),
            median_cover_ratio_on_auction_days=("cover_ratio", "median"),
            nedospros_days=("Flag_Nedospros", "sum"),
            perespros_days=("Flag_Perespros", "sum"),
            avg_yield_spread_bp=("yield_curve_spread_bp", "mean"),
            cover_mad_alert_days=("Signal_Cover_MAD_Alert", "sum"),
            spread_mad_alert_days=("Signal_YieldSpread_MAD_Alert", "sum"),
            stress_days=("Stress_Flag", "sum") if "Stress_Flag" in df.columns else ("has_auction", "sum"),
        )
        .reset_index()
    )

    summary["auction_day_share"] = summary["auction_days"] / summary["calendar_days"]
    summary["nedospros_share_of_auction_days"] = (
        summary["nedospros_days"] / summary["auction_days"].replace(0, np.nan)
    )
    summary["perespros_share_of_auction_days"] = (
        summary["perespros_days"] / summary["auction_days"].replace(0, np.nan)
    )

    return summary


def print_signal_report(df: pd.DataFrame) -> None:
    """Print diagnostics for notebook/script runs."""
    print("Rows:", len(df))
    print("Date range:", df["date"].min(), "->", df["date"].max())
    print("Auction days:", int(df["has_auction"].sum()))
    print("Non-auction days:", int((df["has_auction"] == 0).sum()))

    print("\nSignal coverage:")
    coverage_cols = [
        "cover_ratio",
        "last_cover_ratio",
        "weighted_avg_yield",
        "last_weighted_avg_yield",
        "yield_curve_spread_bp",
        "last_yield_curve_spread_bp",
        "MAD_score_cover",
        "MAD_score_yield_spread",
    ]
    existing = [col for col in coverage_cols if col in df.columns]
    print(df[existing].notna().mean().sort_values(ascending=False))

    print("\nAuction states:")
    print(df["Auction_State"].value_counts(dropna=False))
    print(df["Auction_State"].value_counts(normalize=True, dropna=False).rename("share"))

    print("\nDaily signal states:")
    print(df["Daily_Signal_State"].value_counts(dropna=False))

    print("\nMAD alerts:")
    print(df[["Signal_Cover_MAD_Alert", "Signal_YieldSpread_MAD_Alert"]].sum())

    print("\nMost negative cover MAD scores:")
    print(
        df.sort_values("MAD_score_cover")[[
            "date",
            "has_auction",
            "ofz_issues",
            "cover_ratio",
            "last_cover_ratio",
            "MAD_score_cover",
            "Flag_Nedospros",
            "Flag_Perespros",
            "Daily_Signal_State",
        ]].head(10).to_string(index=False)
    )

    print("\nHighest yield spread MAD scores:")
    print(
        df.sort_values("MAD_score_yield_spread", ascending=False)[[
            "date",
            "has_auction",
            "weighted_avg_yield",
            "last_yield_curve_spread_bp",
            "MAD_score_yield_spread",
            "Daily_Signal_State",
        ]].head(10).to_string(index=False)
    )


def plot_cover_ratio(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df[df["has_auction"].eq(1)].dropna(subset=["date", "cover_ratio_clipped"]).copy()
    plot_df = plot_df.sort_values("date")

    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["date"], plot_df["cover_ratio_clipped"], linewidth=1.2, label="Daily cover ratio, clipped")

    ned = plot_df[plot_df["Flag_Nedospros"] == 1]
    per = plot_df[plot_df["Flag_Perespros"] == 1]

    plt.scatter(ned["date"], ned["cover_ratio_clipped"], s=18, label="Недоспрос")
    plt.scatter(per["date"], per["cover_ratio_clipped"], s=18, label="Переспрос")

    plt.axhline(COVER_NEDOSPROS_THRESHOLD, linestyle="--", linewidth=1, label="Недоспрос < 1.2")
    plt.axhline(COVER_PERESPROS_THRESHOLD, linestyle="--", linewidth=1, label="Переспрос > 2.0")

    plt.title("Daily cover ratio ОФЗ")
    plt.xlabel("Дата")
    plt.ylabel("Cover ratio")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def plot_yield_spread(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df[df["has_auction"].eq(1)].dropna(subset=["date", "yield_curve_spread_bp"]).copy()
    if plot_df.empty:
        print("Yield spread chart skipped: no yield_curve_spread_bp values.")
        return

    plot_df = plot_df.sort_values("date")

    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["date"], plot_df["yield_curve_spread_bp"], linewidth=1.2, label="Yield spread, bp")
    plt.axhline(0, linestyle="--", linewidth=1, label="0 bp")

    alerts = plot_df[plot_df["Signal_YieldSpread_MAD_Alert"] == 1]
    plt.scatter(alerts["date"], alerts["yield_curve_spread_bp"], s=18, label="MAD alert")

    plt.title("Yield spread к кривой ОФЗ")
    plt.xlabel("Дата")
    plt.ylabel("Spread, bp")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def optional_score_quality_check(df: pd.DataFrame) -> None:
    """Directional sanity check, not ML validation."""
    cover_eval = df[df["has_auction"].eq(1)].dropna(subset=["MAD_score_cover", "Flag_Nedospros"]).copy()
    if cover_eval["Flag_Nedospros"].nunique() == 2:
        score = -cover_eval["MAD_score_cover"]
        y = cover_eval["Flag_Nedospros"]
        print("\nDirectional score check: -MAD_score_cover vs Flag_Nedospros")
        print("ROC-AUC:", round(roc_auc_score(y, score), 4))
        print("PR-AUC: ", round(average_precision_score(y, score), 4))

    spread_eval = df.dropna(subset=["MAD_score_yield_spread", "Signal_YieldSpread_MAD_Alert"]).copy()
    if spread_eval["Signal_YieldSpread_MAD_Alert"].nunique() == 2:
        score = spread_eval["MAD_score_yield_spread"].abs()
        y = spread_eval["Signal_YieldSpread_MAD_Alert"]
        print("\nDirectional score check: abs(MAD_score_yield_spread) vs spread MAD alert")
        print("ROC-AUC:", round(roc_auc_score(y, score), 4))
        print("PR-AUC: ", round(average_precision_score(y, score), 4))


def main() -> pd.DataFrame:
    features_path = resolve_features_path()
    print(f"Loading features from: {features_path}")

    df = load_features(features_path)
    df = add_dashboard_states(df)

    summary = build_year_summary(df)

    existing_cols = [col for col in DASHBOARD_COLS if col in df.columns]
    passthrough = [col for col in df.columns if col not in existing_cols]
    signal_df = df[existing_cols + passthrough]

    SIGNALS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    signal_df.to_csv(SIGNALS_DAILY_OUTPUT_PATH, index=False)
    signal_df.to_csv(SIGNALS_OUTPUT_PATH, index=False)
    summary.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    print_signal_report(signal_df)
    optional_score_quality_check(signal_df)
    plot_cover_ratio(signal_df, COVER_CHART_PATH)
    plot_yield_spread(signal_df, SPREAD_CHART_PATH)

    print(f"\nSaved daily signals to: {SIGNALS_DAILY_OUTPUT_PATH}")
    print(f"Saved compatibility signals to: {SIGNALS_OUTPUT_PATH}")
    print(f"Saved yearly summary to: {SUMMARY_OUTPUT_PATH}")
    print(f"Saved cover chart to: {COVER_CHART_PATH}")
    print(f"Saved spread chart to: {SPREAD_CHART_PATH}")

    return signal_df


# %%
if __name__ == "__main__":
    df = main()
