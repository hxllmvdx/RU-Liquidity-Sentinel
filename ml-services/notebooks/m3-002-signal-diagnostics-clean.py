# %%
"""
M3-002: OFZ auction signal diagnostics and dashboard export.

This file replaces the previous Isolation Forest baseline for the current M3
specification.

Why no ML model here:
    The module requirements are deterministic:
        - cover ratio;
        - yield spread against OFZ curve;
        - rolling 3-year MAD scores;
        - Flag_Nedospros and Flag_Perespros;
        - Cover Ratio chart.

    There is no labelled target and no prediction requirement. Therefore an
    unsupervised model such as Isolation Forest is optional research, not a core
    production signal for this module.

Input:
    ../../data/processed/ofz_auction_features.csv
    fallback: /mnt/data/ofz_auction_features.csv

Output:
    ../../data/processed/ofz_auction_signals.csv
    ../../data/processed/ofz_m3_signal_summary.csv
    ../../data/processed/ofz_cover_ratio_dashboard.png
    fallback: /mnt/data/*
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
FEATURES_PATH = PROJECT_DATA_DIR / "ofz_auction_features.csv"
SIGNALS_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_auction_signals.csv"
SUMMARY_OUTPUT_PATH = PROJECT_DATA_DIR / "ofz_m3_signal_summary.csv"
COVER_CHART_PATH = PROJECT_DATA_DIR / "ofz_cover_ratio_dashboard.png"
SPREAD_CHART_PATH = PROJECT_DATA_DIR / "ofz_yield_spread_dashboard.png"

if not FEATURES_PATH.exists():
    FEATURES_PATH = Path("/mnt/data/ofz_auction_features.csv")
    SIGNALS_OUTPUT_PATH = Path("/mnt/data/ofz_auction_signals.csv")
    SUMMARY_OUTPUT_PATH = Path("/mnt/data/ofz_m3_signal_summary.csv")
    COVER_CHART_PATH = Path("/mnt/data/ofz_cover_ratio_dashboard.png")
    SPREAD_CHART_PATH = Path("/mnt/data/ofz_yield_spread_dashboard.png")

COVER_NEDOSPROS_THRESHOLD = 1.2
COVER_PERESPROS_THRESHOLD = 2.0
MAD_ALERT_ABS_THRESHOLD = 2.0

REQUIRED_COLS = [
    "auction_date",
    "ofz_issue",
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "yield_curve_spread_bp",
    "MAD_score_cover",
    "MAD_score_yield_spread",
    "Flag_Nedospros",
    "Flag_Perespros",
]

DASHBOARD_COLS = [
    "auction_date",
    "ofz_issue",
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "cover_ratio_clipped",
    "weighted_avg_yield",
    "yield_curve_spread_bp",
    "MAD_score_cover",
    "MAD_score_yield_spread",
    "Flag_Nedospros",
    "Flag_Perespros",
    "Signal_Cover_MAD_Alert",
    "Signal_YieldSpread_MAD_Alert",
    "Auction_State",
]

# %%
# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def load_features(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Feature file not found: {path}")

    df = pd.read_csv(path)
    df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce")
    df = df.sort_values(["auction_date", "ofz_issue"]).reset_index(drop=True)

    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    numeric_cols = [
        "offer_volume_bln_rub",
        "demand_volume_bln_rub",
        "placement_volume_bln_rub",
        "cover_ratio",
        "cover_ratio_clipped",
        "weighted_avg_yield",
        "yield_curve_spread_bp",
        "MAD_score_cover",
        "MAD_score_yield_spread",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["Flag_Nedospros", "Flag_Perespros"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

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

    df["Auction_State"] = np.select(
        condlist=[
            df["Flag_Nedospros"] == 1,
            df["Flag_Perespros"] == 1,
        ],
        choicelist=["nedospros", "perespros"],
        default="neutral",
    )

    return df


def build_year_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate required signals by year for quick reporting."""
    summary = (
        df.assign(year=df["auction_date"].dt.year)
        .groupby("year", dropna=False)
        .agg(
            auctions=("ofz_issue", "count"),
            avg_cover_ratio=("cover_ratio", "mean"),
            median_cover_ratio=("cover_ratio", "median"),
            nedospros_count=("Flag_Nedospros", "sum"),
            perespros_count=("Flag_Perespros", "sum"),
            avg_yield_spread_bp=("yield_curve_spread_bp", "mean"),
            cover_mad_alerts=("Signal_Cover_MAD_Alert", "sum"),
            spread_mad_alerts=("Signal_YieldSpread_MAD_Alert", "sum"),
        )
        .reset_index()
    )

    summary["nedospros_share"] = summary["nedospros_count"] / summary["auctions"]
    summary["perespros_share"] = summary["perespros_count"] / summary["auctions"]

    return summary


def print_signal_report(df: pd.DataFrame) -> None:
    """Print diagnostics for notebook/script runs."""
    print("Rows:", len(df))
    print("Date range:", df["auction_date"].min(), "->", df["auction_date"].max())

    print("\nSignal coverage:")
    coverage_cols = [
        "cover_ratio",
        "weighted_avg_yield",
        "yield_curve_spread_bp",
        "MAD_score_cover",
        "MAD_score_yield_spread",
    ]
    print(df[coverage_cols].notna().mean().sort_values(ascending=False))

    print("\nAuction states:")
    print(df["Auction_State"].value_counts(dropna=False))
    print(df["Auction_State"].value_counts(normalize=True, dropna=False).rename("share"))

    print("\nMAD alerts:")
    print(df[["Signal_Cover_MAD_Alert", "Signal_YieldSpread_MAD_Alert"]].sum())

    print("\nMost negative cover MAD scores:")
    print(
        df.sort_values("MAD_score_cover")[[
            "auction_date",
            "ofz_issue",
            "cover_ratio",
            "MAD_score_cover",
            "Flag_Nedospros",
            "Flag_Perespros",
        ]].head(10).to_string(index=False)
    )

    print("\nHighest yield spread MAD scores:")
    print(
        df.sort_values("MAD_score_yield_spread", ascending=False)[[
            "auction_date",
            "ofz_issue",
            "weighted_avg_yield",
            "yield_curve_spread_bp",
            "MAD_score_yield_spread",
        ]].head(10).to_string(index=False)
    )


def plot_cover_ratio(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df.dropna(subset=["auction_date", "cover_ratio_clipped"]).copy()
    plot_df = plot_df.sort_values("auction_date")

    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["auction_date"], plot_df["cover_ratio_clipped"], linewidth=1.2, label="Cover ratio, clipped")

    ned = plot_df[plot_df["Flag_Nedospros"] == 1]
    per = plot_df[plot_df["Flag_Perespros"] == 1]

    plt.scatter(ned["auction_date"], ned["cover_ratio_clipped"], s=18, label="Недоспрос")
    plt.scatter(per["auction_date"], per["cover_ratio_clipped"], s=18, label="Переспрос")

    plt.axhline(COVER_NEDOSPROS_THRESHOLD, linestyle="--", linewidth=1, label="Недоспрос < 1.2")
    plt.axhline(COVER_PERESPROS_THRESHOLD, linestyle="--", linewidth=1, label="Переспрос > 2.0")

    plt.title("Cover ratio ОФЗ")
    plt.xlabel("Дата аукциона")
    plt.ylabel("Cover ratio")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def plot_yield_spread(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df.dropna(subset=["auction_date", "yield_curve_spread_bp"]).copy()
    if plot_df.empty:
        print("Yield spread chart skipped: no yield_curve_spread_bp values.")
        return

    plot_df = plot_df.sort_values("auction_date")

    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["auction_date"], plot_df["yield_curve_spread_bp"], linewidth=1.2, label="Yield spread, bp")
    plt.axhline(0, linestyle="--", linewidth=1, label="0 bp")

    alerts = plot_df[plot_df["Signal_YieldSpread_MAD_Alert"] == 1]
    plt.scatter(alerts["auction_date"], alerts["yield_curve_spread_bp"], s=18, label="MAD alert")

    plt.title("Yield spread к кривой ОФЗ")
    plt.xlabel("Дата аукциона")
    plt.ylabel("Spread, bp")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def optional_score_quality_check(df: pd.DataFrame) -> None:
    """
    Optional check: do MAD scores rank the raw flags in a sensible way?

    This is not ML validation. It only confirms that continuous MAD scores are
    directionally aligned with deterministic flags.
    """
    cover_eval = df.dropna(subset=["MAD_score_cover", "Flag_Nedospros"]).copy()
    if cover_eval["Flag_Nedospros"].nunique() == 2:
        # For nedospros, lower cover MAD is more risky, hence minus sign.
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
    df = load_features(FEATURES_PATH)
    df = add_dashboard_states(df)

    summary = build_year_summary(df)

    existing_cols = [col for col in DASHBOARD_COLS if col in df.columns]
    passthrough = [col for col in df.columns if col not in existing_cols]
    signal_df = df[existing_cols + passthrough]

    SIGNALS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    signal_df.to_csv(SIGNALS_OUTPUT_PATH, index=False)
    summary.to_csv(SUMMARY_OUTPUT_PATH, index=False)

    print_signal_report(signal_df)
    optional_score_quality_check(signal_df)
    plot_cover_ratio(signal_df, COVER_CHART_PATH)
    plot_yield_spread(signal_df, SPREAD_CHART_PATH)

    print(f"\nSaved signals to: {SIGNALS_OUTPUT_PATH}")
    print(f"Saved yearly summary to: {SUMMARY_OUTPUT_PATH}")
    print(f"Saved cover chart to: {COVER_CHART_PATH}")
    print(f"Saved spread chart to: {SPREAD_CHART_PATH}")

    return signal_df


# %%
if __name__ == "__main__":
    df = main()
