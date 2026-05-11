# %%
"""
M5-002: Treasury signal diagnostics and dashboard export.

Input:
    ../../data/processed/treasury/m5_treasury/m5_treasury_feature_clean.csv
    fallback raw: ../../data/raw/treasury/m5_treasury/m5_treasury_features_2021-01-01_2026-05-10.csv
    fallback /mnt/data/*

Output:
    ../../data/processed/treasury/m5_treasury/m5_treasury_signals.csv
    ../../data/processed/treasury/m5_treasury/m5_treasury_signal_summary.csv
    ../../data/processed/treasury/m5_treasury/m5_treasury_cbr_weekly_flow_dashboard.png
    ../../data/processed/treasury/m5_treasury/m5_treasury_roskazna_weekly_change_dashboard.png
    ../../data/processed/treasury/m5_treasury/m5_treasury_budget_drain_score_dashboard.png
    fallback: /mnt/data/*

Why no ML model here:
    The M5 requirements are deterministic:
        - weekly/monthly deltas;
        - rolling 3-year MAD scores;
        - threshold flag for budget drain;
        - dashboard chart.
    Ground truth structural liquidity is used as a diagnostic reference, not as
    a supervised target for this MVP module.
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
PROCESSED_RELATIVE_DIR = Path("data/processed/treasury/m5_treasury")
RAW_RELATIVE_PATH = Path("data/raw/treasury/m5_treasury/m5_treasury_features_2021-01-01_2026-05-10.csv")

FEATURES_FILENAME = "m5_treasury_feature_clean.csv"
SIGNALS_FILENAME = "m5_treasury_signals.csv"
SUMMARY_FILENAME = "m5_treasury_signal_summary.csv"

CBR_FLOW_CHART_FILENAME = "m5_treasury_cbr_weekly_flow_dashboard.png"
ROSKAZNA_CHART_FILENAME = "m5_treasury_roskazna_weekly_change_dashboard.png"
SCORE_CHART_FILENAME = "m5_treasury_budget_drain_score_dashboard.png"
BALANCE_CHART_FILENAME = "m5_treasury_balance_dashboard.png"

FALLBACK_DIR = Path("/mnt/data")

CBR_ABSOLUTE_DRAIN_THRESHOLD = -300.0
CBR_SEVERE_DRAIN_THRESHOLD = -500.0
ROSKAZNA_DEPOSIT_DROP_THRESHOLD = -1500.0

REQUIRED_COLS = [
    "date",
    "cbr_eks_balance_bln_rub",
    "roskazna_deposit_placements_bln_rub",
    "cbr_weekly_delta_bln_rub",
    "cbr_monthly_delta_bln_rub",
    "roskazna_weekly_delta_bln_rub",
    "roskazna_monthly_delta_bln_rub",
    "MAD_score_CBR",
    "MAD_score_Roskazna",
    "Flag_CBR_Absolute_Drain",
    "Flag_CBR_Severe_Absolute_Drain",
    "Flag_CBR_MAD_Drain",
    "Flag_Roskazna_Absolute_Deposit_Drop",
    "Flag_Roskazna_MAD_Deposit_Drop",
    "Flag_Budget_Drain",
    "Budget_Drain_State",
    "Budget_Drain_Score",
    "structural_liquidity_balance_bln_rub",
]

DASHBOARD_COLS = [
    "date",
    "cbr_eks_balance_bln_rub",
    "cbr_weekly_delta_bln_rub",
    "cbr_monthly_delta_bln_rub",
    "roskazna_deposit_placements_bln_rub",
    "roskazna_weekly_delta_bln_rub",
    "roskazna_monthly_delta_bln_rub",
    "participant_banks_count",
    "MAD_score_CBR",
    "MAD_score_Roskazna",
    "Flag_CBR_Absolute_Drain",
    "Flag_CBR_Severe_Absolute_Drain",
    "Flag_CBR_MAD_Drain",
    "Flag_Roskazna_Absolute_Deposit_Drop",
    "Flag_Roskazna_MAD_Deposit_Drop",
    "Flag_Budget_Drain",
    "Budget_Drain_State",
    "Budget_Drain_Score",
    "Budget_Drain_Level",
    "Dashboard_Color",
    "structural_liquidity_balance_bln_rub",
    "structural_liquidity_weekly_delta_bln_rub",
    "GroundTruth_Liquidity_Deterioration",
]

# %%
# -----------------------------------------------------------------------------
# Path helpers: notebook-safe, no __file__
# -----------------------------------------------------------------------------
def candidate_roots() -> list[Path]:
    roots: list[Path] = []
    start = Path.cwd().resolve()
    roots.extend([start, *start.parents])
    roots.append(FALLBACK_DIR)

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            unique_roots.append(root)
            seen.add(root)
    return unique_roots


def resolve_paths() -> dict[str, Path]:
    for root in candidate_roots():
        processed_dir = root / PROCESSED_RELATIVE_DIR
        features_path = processed_dir / FEATURES_FILENAME
        if features_path.exists():
            return {
                "features": features_path,
                "processed_dir": processed_dir,
                "signals": processed_dir / SIGNALS_FILENAME,
                "summary": processed_dir / SUMMARY_FILENAME,
                "cbr_flow_chart": processed_dir / CBR_FLOW_CHART_FILENAME,
                "roskazna_chart": processed_dir / ROSKAZNA_CHART_FILENAME,
                "score_chart": processed_dir / SCORE_CHART_FILENAME,
                "balance_chart": processed_dir / BALANCE_CHART_FILENAME,
            }

    fallback_features = FALLBACK_DIR / FEATURES_FILENAME
    if fallback_features.exists():
        return {
            "features": fallback_features,
            "processed_dir": FALLBACK_DIR,
            "signals": FALLBACK_DIR / SIGNALS_FILENAME,
            "summary": FALLBACK_DIR / SUMMARY_FILENAME,
            "cbr_flow_chart": FALLBACK_DIR / CBR_FLOW_CHART_FILENAME,
            "roskazna_chart": FALLBACK_DIR / ROSKAZNA_CHART_FILENAME,
            "score_chart": FALLBACK_DIR / SCORE_CHART_FILENAME,
            "balance_chart": FALLBACK_DIR / BALANCE_CHART_FILENAME,
        }

    searched = [str(root / PROCESSED_RELATIVE_DIR / FEATURES_FILENAME) for root in candidate_roots()]
    raise FileNotFoundError("M5 processed feature dataset not found. Run M5-001 first. Searched:\n" + "\n".join(searched))

# %%
# -----------------------------------------------------------------------------
# Load + diagnostics helpers
# -----------------------------------------------------------------------------
def load_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    text_cols = {"Budget_Drain_State", "source_code", "raw_refs", "loaded_at", "cbr_balance_scale_note"}
    for col in df.columns:
        if col != "date" and col not in text_cols:
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().sum() > 0:
                df[col] = converted

    flag_cols = [col for col in df.columns if col.startswith("Flag_") or col == "GroundTruth_Liquidity_Deterioration"]
    for col in flag_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def add_dashboard_states(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Budget_Drain_Level"] = pd.cut(
        df["Budget_Drain_Score"],
        bins=[-0.01, 0.01, 0.35, 0.70, 1.00],
        labels=["normal", "watch", "warning", "stress"],
    )

    df["Dashboard_Color"] = np.select(
        condlist=[
            df["Budget_Drain_Level"].astype(str) == "stress",
            df["Budget_Drain_Level"].astype(str) == "warning",
            df["Budget_Drain_Level"].astype(str) == "watch",
        ],
        choicelist=["red", "orange", "yellow"],
        default="green",
    )

    return df


def build_year_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.assign(year=df["date"].dt.year)
        .groupby("year", dropna=False)
        .agg(
            weeks=("date", "count"),
            avg_cbr_balance_bln_rub=("cbr_eks_balance_bln_rub", "mean"),
            min_cbr_weekly_delta_bln_rub=("cbr_weekly_delta_bln_rub", "min"),
            min_roskazna_weekly_delta_bln_rub=("roskazna_weekly_delta_bln_rub", "min"),
            cbr_absolute_drains=("Flag_CBR_Absolute_Drain", "sum"),
            cbr_mad_drains=("Flag_CBR_MAD_Drain", "sum"),
            roskazna_absolute_drops=("Flag_Roskazna_Absolute_Deposit_Drop", "sum"),
            roskazna_mad_drops=("Flag_Roskazna_MAD_Deposit_Drop", "sum"),
            budget_drain_count=("Flag_Budget_Drain", "sum"),
            avg_budget_drain_score=("Budget_Drain_Score", "mean"),
        )
        .reset_index()
    )
    summary["budget_drain_share"] = summary["budget_drain_count"] / summary["weeks"]
    return summary


def print_signal_report(df: pd.DataFrame) -> None:
    print("Rows:", len(df))
    print("Date range:", df["date"].min(), "->", df["date"].max())

    print("\nSignal coverage:")
    coverage_cols = [
        "cbr_eks_balance_bln_rub",
        "roskazna_deposit_placements_bln_rub",
        "cbr_weekly_delta_bln_rub",
        "roskazna_weekly_delta_bln_rub",
        "MAD_score_CBR",
        "MAD_score_Roskazna",
        "structural_liquidity_balance_bln_rub",
        "participant_banks_count",
    ]
    print(df[coverage_cols].notna().mean().sort_values(ascending=False))

    print("\nBudget drain states:")
    print(df["Budget_Drain_State"].value_counts(dropna=False))
    print(df["Budget_Drain_State"].value_counts(normalize=True, dropna=False).rename("share"))

    print("\nSignal reasons:")
    reason_cols = [
        "Flag_CBR_Absolute_Drain",
        "Flag_CBR_Severe_Absolute_Drain",
        "Flag_CBR_MAD_Drain",
        "Flag_Roskazna_Absolute_Deposit_Drop",
        "Flag_Roskazna_MAD_Deposit_Drop",
        "Flag_Budget_Drain",
    ]
    print(df[reason_cols].sum().sort_values(ascending=False))

    print("\nDashboard levels:")
    print(df["Budget_Drain_Level"].value_counts(dropna=False))

    print("\nLargest CBR weekly drains:")
    cols = [
        "date",
        "cbr_eks_balance_bln_rub",
        "cbr_weekly_delta_bln_rub",
        "MAD_score_CBR",
        "roskazna_deposit_placements_bln_rub",
        "roskazna_weekly_delta_bln_rub",
        "MAD_score_Roskazna",
        "Budget_Drain_State",
        "Budget_Drain_Level",
    ]
    print(df.sort_values("cbr_weekly_delta_bln_rub")[cols].head(10).to_string(index=False))


def optional_ground_truth_check(df: pd.DataFrame) -> None:
    eval_df = df.dropna(subset=["Budget_Drain_Score", "GroundTruth_Liquidity_Deterioration"]).copy()
    if eval_df["GroundTruth_Liquidity_Deterioration"].nunique() == 2:
        print("\nGround truth directional check: Budget_Drain_Score vs liquidity deterioration")
        print("ROC-AUC:", round(roc_auc_score(eval_df["GroundTruth_Liquidity_Deterioration"], eval_df["Budget_Drain_Score"]), 4))
        print("PR-AUC: ", round(average_precision_score(eval_df["GroundTruth_Liquidity_Deterioration"], eval_df["Budget_Drain_Score"]), 4))

# %%
# -----------------------------------------------------------------------------
# Plot helpers
# -----------------------------------------------------------------------------
def plot_cbr_weekly_flow(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df.dropna(subset=["date", "cbr_weekly_delta_bln_rub"]).copy()
    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["date"], plot_df["cbr_weekly_delta_bln_rub"], linewidth=1.2, label="Недельный приток/отток")
    plt.axhline(0, linestyle="--", linewidth=1, label="0")
    plt.axhline(CBR_ABSOLUTE_DRAIN_THRESHOLD, linestyle="--", linewidth=1, label="-300 млрд")
    plt.axhline(CBR_SEVERE_DRAIN_THRESHOLD, linestyle="--", linewidth=1, label="-500 млрд")
    alerts = plot_df[plot_df["Flag_CBR_Absolute_Drain"] == 1]
    plt.scatter(alerts["date"], alerts["cbr_weekly_delta_bln_rub"], s=24, label="CBR drain")
    plt.title("Приток/Отток казначейства: недельная delta ЦБ/SORS")
    plt.xlabel("Дата")
    plt.ylabel("млрд руб.")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def plot_roskazna_weekly_change(df: pd.DataFrame, output_path: Path) -> None:
    plot_df = df.dropna(subset=["date", "roskazna_weekly_delta_bln_rub"]).copy()
    plt.figure(figsize=(14, 6))
    plt.plot(plot_df["date"], plot_df["roskazna_weekly_delta_bln_rub"], linewidth=1.2, label="Изменение размещений Росказны")
    plt.axhline(0, linestyle="--", linewidth=1, label="0")
    plt.axhline(ROSKAZNA_DEPOSIT_DROP_THRESHOLD, linestyle="--", linewidth=1, label="Порог падения")
    alerts = plot_df[plot_df["Flag_Roskazna_Absolute_Deposit_Drop"] == 1]
    plt.scatter(alerts["date"], alerts["roskazna_weekly_delta_bln_rub"], s=24, label="Deposit drop")
    plt.title("Недельное изменение размещений ЕКС на банковских депозитах")
    plt.xlabel("Дата")
    plt.ylabel("млрд руб.")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def plot_budget_drain_score(df: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(14, 6))
    plt.plot(df["date"], df["Budget_Drain_Score"], linewidth=1.2, label="Budget Drain Score")
    flagged = df[df["Flag_Budget_Drain"] == 1]
    plt.scatter(flagged["date"], flagged["Budget_Drain_Score"], s=24, label="Flag_Budget_Drain")
    plt.title("Budget Drain Score")
    plt.xlabel("Дата")
    plt.ylabel("Score")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()


def plot_balance_dashboard(df: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(14, 6))
    plt.plot(df["date"], df["cbr_eks_balance_bln_rub"], linewidth=1.2, label="Остатки бюджетных средств / ЕКС proxy")
    plt.plot(df["date"], df["structural_liquidity_balance_bln_rub"], linewidth=1.2, label="Структурная ликвидность ЦБ")
    plt.title("Бюджетные средства и структурная ликвидность")
    plt.xlabel("Дата")
    plt.ylabel("млрд руб.")
    plt.legend()
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=160)
    plt.show()

# %%
# -----------------------------------------------------------------------------
# Run diagnostics + export
# -----------------------------------------------------------------------------
paths = resolve_paths()
df = load_features(paths["features"])
df = add_dashboard_states(df)
summary = build_year_summary(df)

existing_cols = [col for col in DASHBOARD_COLS if col in df.columns]
passthrough = [col for col in df.columns if col not in existing_cols]
signal_df = df[existing_cols + passthrough]

paths["processed_dir"].mkdir(parents=True, exist_ok=True)
signal_df.to_csv(paths["signals"], index=False)
summary.to_csv(paths["summary"], index=False)

print("Input:", paths["features"])
print_signal_report(signal_df)
optional_ground_truth_check(signal_df)

plot_cbr_weekly_flow(signal_df, paths["cbr_flow_chart"])
plot_roskazna_weekly_change(signal_df, paths["roskazna_chart"])
plot_budget_drain_score(signal_df, paths["score_chart"])
plot_balance_dashboard(signal_df, paths["balance_chart"])

print(f"\nSaved signals to: {paths['signals']}")
print(f"Saved signal summary to: {paths['summary']}")
print(f"Saved CBR flow chart to: {paths['cbr_flow_chart']}")
print(f"Saved Roskazna chart to: {paths['roskazna_chart']}")
print(f"Saved score chart to: {paths['score_chart']}")
print(f"Saved balance chart to: {paths['balance_chart']}")

signal_df.head(20)
