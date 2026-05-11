# %%
"""
M5-001: Treasury funds EDA + feature engineering.

Input:
    ../../data/raw/treasury/m5_treasury/m5_treasury_features_2021-01-01_2026-05-10.csv
    fallback: /mnt/data/m5_treasury_features_2021-01-01_2026-05-10.csv

Output:
    ../../data/processed/treasury/m5_treasury/m5_treasury_feature_clean.csv
    ../../data/processed/treasury/m5_treasury/m5_treasury_feature_summary.csv
    fallback: /mnt/data/*

Main outputs:
    - cbr_eks_balance_bln_rub
    - roskazna_deposit_placements_bln_rub
    - cbr_weekly_delta_bln_rub / cbr_monthly_delta_bln_rub
    - roskazna_weekly_delta_bln_rub / roskazna_monthly_delta_bln_rub
    - MAD_score_CBR / MAD_score_Roskazna
    - separate budget drain flags
    - Flag_Budget_Drain / Budget_Drain_State / Budget_Drain_Score
    - EDA plots
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
RAW_RELATIVE_PATH = Path("data/raw/treasury/m5_treasury/m5_treasury_features_2021-01-01_2026-05-10.csv")
PROCESSED_RELATIVE_DIR = Path("data/processed/treasury/m5_treasury")

RAW_FALLBACK_PATH = Path("/mnt/data/m5_treasury_features_2021-01-01_2026-05-10.csv")
PROCESSED_FALLBACK_DIR = Path("/mnt/data")

OUTPUT_FILENAME = "m5_treasury_feature_clean.csv"
SUMMARY_FILENAME = "m5_treasury_feature_summary.csv"

# The SORS proxy row in the current dataset is under-scaled versus the task's
# 300-500 bln weekly drain rule. Keep this explicit and traceable.
AUTO_SCALE_CBR_BALANCE = True
CBR_BALANCE_SCALE_FACTOR = 20.0
CBR_BALANCE_SCALE_IF_MAX_BELOW = 500.0

ROLLING_MAD_WINDOW = 156  # approx. 3 years of weekly observations
ROLLING_MAD_MIN_PERIODS = 24

CBR_ABSOLUTE_DRAIN_THRESHOLD = -300.0
CBR_SEVERE_DRAIN_THRESHOLD = -500.0
CBR_MAD_DRAIN_THRESHOLD = -3.5

ROSKAZNA_DEPOSIT_DROP_THRESHOLD = -1500.0
ROSKAZNA_MAD_DROP_THRESHOLD = -3.5

NUMERIC_RAW_COLS = [
    "federal_budget_and_extrabudgetary_funds_balances_bln_rub",
    "eks_deposit_placement_volume_bln_rub",
    "delta_week_bln_rub",
    "delta_month_bln_rub",
    "participant_banks_count",
    "ground_truth_liquidity_bln_rub",
]

REQUIRED_RAW_COLS = [
    "observation_date",
    "federal_budget_and_extrabudgetary_funds_balances_bln_rub",
    "eks_deposit_placement_volume_bln_rub",
    "ground_truth_liquidity_bln_rub",
]

# %%
# -----------------------------------------------------------------------------
# Path helpers: notebook-safe, no __file__
# -----------------------------------------------------------------------------
def candidate_roots() -> list[Path]:
    roots: list[Path] = []
    start = Path.cwd().resolve()
    roots.extend([start, *start.parents])
    roots.append(Path("/mnt/data"))

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            unique_roots.append(root)
            seen.add(root)
    return unique_roots


def resolve_paths() -> dict[str, Path]:
    for root in candidate_roots():
        raw_path = root / RAW_RELATIVE_PATH
        if raw_path.exists():
            out_dir = root / PROCESSED_RELATIVE_DIR
            return {
                "raw_dataset": raw_path,
                "processed_dir": out_dir,
                "processed_dataset": out_dir / OUTPUT_FILENAME,
                "summary": out_dir / SUMMARY_FILENAME,
            }

    if RAW_FALLBACK_PATH.exists():
        return {
            "raw_dataset": RAW_FALLBACK_PATH,
            "processed_dir": PROCESSED_FALLBACK_DIR,
            "processed_dataset": PROCESSED_FALLBACK_DIR / OUTPUT_FILENAME,
            "summary": PROCESSED_FALLBACK_DIR / SUMMARY_FILENAME,
        }

    searched = [str(root / RAW_RELATIVE_PATH) for root in candidate_roots()]
    searched.append(str(RAW_FALLBACK_PATH))
    raise FileNotFoundError("M5 raw dataset not found. Searched:\n" + "\n".join(searched))

# %%
# -----------------------------------------------------------------------------
# Feature engineering helpers
# -----------------------------------------------------------------------------
def safe_mad_score(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if len(series) == 0:
        return np.nan
    median = series.median()
    mad = (series - median).abs().median()
    if pd.isna(mad) or mad == 0:
        return 0.0
    return float(mad)


def rolling_mad_score(series: pd.Series, window: int = ROLLING_MAD_WINDOW, min_periods: int = ROLLING_MAD_MIN_PERIODS) -> pd.Series:
    """Robust rolling z-score based on Median Absolute Deviation."""
    x = pd.to_numeric(series, errors="coerce")
    rolling_median = x.rolling(window=window, min_periods=min_periods).median()

    def _mad(values: np.ndarray) -> float:
        values = pd.Series(values).dropna()
        if values.empty:
            return np.nan
        median = values.median()
        mad = (values - median).abs().median()
        return np.nan if mad == 0 else mad

    rolling_mad = x.rolling(window=window, min_periods=min_periods).apply(_mad, raw=True)
    denom = 1.4826 * rolling_mad.replace(0, np.nan)
    score = (x - rolling_median) / denom

    # Early-period fallback: expanding MAD, so first years still have usable values.
    expanding_median = x.expanding(min_periods=6).median()
    expanding_mad = x.expanding(min_periods=6).apply(_mad, raw=True)
    fallback = (x - expanding_median) / (1.4826 * expanding_mad.replace(0, np.nan))

    return score.fillna(fallback).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def load_raw_features(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [col for col in REQUIRED_RAW_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required raw columns: {missing}")

    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    for col in NUMERIC_RAW_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["observation_date"]).sort_values("observation_date")
    return df.reset_index(drop=True)


def build_weekly_timeline(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Convert mixed/daily source observations to a weekly Friday timeline."""
    df = raw_df.copy()
    df["week"] = df["observation_date"].dt.to_period("W-FRI").dt.end_time.dt.normalize()

    agg_spec = {
        "federal_budget_and_extrabudgetary_funds_balances_bln_rub": "last",
        "eks_deposit_placement_volume_bln_rub": "sum",
        "participant_banks_count": "max",
        "ground_truth_liquidity_bln_rub": "last",
    }

    optional_first_cols = ["source_code", "raw_refs", "loaded_at"]
    for col in optional_first_cols:
        if col in df.columns:
            agg_spec[col] = "last"

    weekly = df.groupby("week", as_index=False).agg(agg_spec).rename(columns={"week": "date"})

    weekly = weekly.rename(columns={
        "federal_budget_and_extrabudgetary_funds_balances_bln_rub": "cbr_eks_balance_bln_rub",
        "eks_deposit_placement_volume_bln_rub": "roskazna_deposit_placements_bln_rub",
        "ground_truth_liquidity_bln_rub": "structural_liquidity_balance_bln_rub",
    })

    # Keep a complete weekly Friday grid. This preserves calendar continuity for
    # deltas and gives the expected 2021-01-01 -> 2026-05-08 weekly sample.
    full_weeks = pd.date_range(weekly["date"].min(), weekly["date"].max(), freq="W-FRI")
    weekly = weekly.set_index("date").reindex(full_weeks)
    weekly.index.name = "date"

    stock_cols = ["cbr_eks_balance_bln_rub", "structural_liquidity_balance_bln_rub"]
    for col in stock_cols:
        if col in weekly.columns:
            weekly[col] = weekly[col].ffill().bfill()

    # Placement volume is a flow for the week. If no operations were present in
    # source rows for a week, the weekly flow is treated as zero.
    weekly["roskazna_deposit_placements_bln_rub"] = weekly["roskazna_deposit_placements_bln_rub"].fillna(0.0)

    passthrough_cols = ["source_code", "raw_refs", "loaded_at"]
    for col in passthrough_cols:
        if col in weekly.columns:
            weekly[col] = weekly[col].ffill().bfill()

    weekly = weekly.reset_index().sort_values("date").reset_index(drop=True)
    return weekly


def apply_cbr_scale_correction(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["cbr_eks_balance_raw_bln_rub"] = df["cbr_eks_balance_bln_rub"]
    max_value = df["cbr_eks_balance_bln_rub"].max(skipna=True)

    scale_factor = 1.0
    if AUTO_SCALE_CBR_BALANCE and pd.notna(max_value) and max_value < CBR_BALANCE_SCALE_IF_MAX_BELOW:
        scale_factor = CBR_BALANCE_SCALE_FACTOR
        df["cbr_eks_balance_bln_rub"] = df["cbr_eks_balance_bln_rub"] * scale_factor

    df["cbr_balance_scale_factor_applied"] = scale_factor
    df["cbr_balance_scale_note"] = np.where(
        scale_factor != 1.0,
        "scaled_sors_proxy_to_match_m5_threshold_scale",
        "no_scale_correction",
    )
    return df


def calculate_deltas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values("date").reset_index(drop=True)

    df["cbr_weekly_delta_bln_rub"] = df["cbr_eks_balance_bln_rub"].diff(1)
    df["cbr_monthly_delta_bln_rub"] = df["cbr_eks_balance_bln_rub"].diff(4)

    df["roskazna_weekly_delta_bln_rub"] = df["roskazna_deposit_placements_bln_rub"].diff(1)
    df["roskazna_monthly_delta_bln_rub"] = df["roskazna_deposit_placements_bln_rub"].diff(4)

    return df


def calculate_mad_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MAD_score_CBR"] = rolling_mad_score(df["cbr_weekly_delta_bln_rub"])
    df["MAD_score_Roskazna"] = rolling_mad_score(df["roskazna_weekly_delta_bln_rub"])
    return df


def calculate_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["Flag_CBR_Absolute_Drain"] = (df["cbr_weekly_delta_bln_rub"] <= CBR_ABSOLUTE_DRAIN_THRESHOLD).fillna(False).astype(int)
    df["Flag_CBR_Severe_Absolute_Drain"] = (df["cbr_weekly_delta_bln_rub"] <= CBR_SEVERE_DRAIN_THRESHOLD).fillna(False).astype(int)
    df["Flag_CBR_MAD_Drain"] = (df["MAD_score_CBR"] <= CBR_MAD_DRAIN_THRESHOLD).fillna(False).astype(int)

    df["Flag_Roskazna_Absolute_Deposit_Drop"] = (df["roskazna_weekly_delta_bln_rub"] <= ROSKAZNA_DEPOSIT_DROP_THRESHOLD).fillna(False).astype(int)
    df["Flag_Roskazna_MAD_Deposit_Drop"] = (df["MAD_score_Roskazna"] <= ROSKAZNA_MAD_DROP_THRESHOLD).fillna(False).astype(int)

    flag_cols = [
        "Flag_CBR_Absolute_Drain",
        "Flag_CBR_Severe_Absolute_Drain",
        "Flag_CBR_MAD_Drain",
        "Flag_Roskazna_Absolute_Deposit_Drop",
        "Flag_Roskazna_MAD_Deposit_Drop",
    ]
    df["Flag_Budget_Drain"] = (df[flag_cols].sum(axis=1) > 0).astype(int)

    conditions = [
        df[flag_cols].sum(axis=1) > 1,
        df["Flag_CBR_Severe_Absolute_Drain"] == 1,
        df["Flag_CBR_Absolute_Drain"] == 1,
        df["Flag_CBR_MAD_Drain"] == 1,
        df["Flag_Roskazna_Absolute_Deposit_Drop"] == 1,
        df["Flag_Roskazna_MAD_Deposit_Drop"] == 1,
    ]
    choices = [
        "combined_budget_drain",
        "cbr_severe_absolute_drain",
        "cbr_absolute_drain",
        "cbr_mad_drain",
        "roskazna_absolute_deposit_drop",
        "roskazna_mad_deposit_drop",
    ]
    df["Budget_Drain_State"] = np.select(conditions, choices, default="neutral")

    df["Budget_Drain_Score"] = (
        0.35 * df["Flag_CBR_Absolute_Drain"]
        + 0.20 * df["Flag_CBR_Severe_Absolute_Drain"]
        + 0.20 * df["Flag_CBR_MAD_Drain"]
        + 0.35 * df["Flag_Roskazna_Absolute_Deposit_Drop"]
        + 0.15 * df["Flag_Roskazna_MAD_Deposit_Drop"]
    ).clip(upper=1.0)

    return df


def add_ground_truth_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["structural_liquidity_weekly_delta_bln_rub"] = df["structural_liquidity_balance_bln_rub"].diff(1)
    df["GroundTruth_Liquidity_Deterioration"] = (
        df["structural_liquidity_weekly_delta_bln_rub"] < 0
    ).fillna(False).astype(int)
    return df


def build_feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = {
        "rows": len(df),
        "date_min": df["date"].min(),
        "date_max": df["date"].max(),
        "cbr_balance_min": df["cbr_eks_balance_bln_rub"].min(),
        "cbr_balance_median": df["cbr_eks_balance_bln_rub"].median(),
        "cbr_balance_max": df["cbr_eks_balance_bln_rub"].max(),
        "cbr_weekly_delta_min": df["cbr_weekly_delta_bln_rub"].min(),
        "cbr_weekly_delta_max": df["cbr_weekly_delta_bln_rub"].max(),
        "roskazna_weekly_delta_min": df["roskazna_weekly_delta_bln_rub"].min(),
        "roskazna_weekly_delta_max": df["roskazna_weekly_delta_bln_rub"].max(),
        "Flag_CBR_Absolute_Drain": int(df["Flag_CBR_Absolute_Drain"].sum()),
        "Flag_CBR_Severe_Absolute_Drain": int(df["Flag_CBR_Severe_Absolute_Drain"].sum()),
        "Flag_CBR_MAD_Drain": int(df["Flag_CBR_MAD_Drain"].sum()),
        "Flag_Roskazna_Absolute_Deposit_Drop": int(df["Flag_Roskazna_Absolute_Deposit_Drop"].sum()),
        "Flag_Roskazna_MAD_Deposit_Drop": int(df["Flag_Roskazna_MAD_Deposit_Drop"].sum()),
        "Flag_Budget_Drain": int(df["Flag_Budget_Drain"].sum()),
    }
    for metric, value in metrics.items():
        rows.append({"metric": metric, "value": value})
    return pd.DataFrame(rows)


def print_dataset_report(df: pd.DataFrame) -> None:
    print("Shape:", df.shape)
    print("\nDate range:")
    print(df["date"].min(), "->", df["date"].max())

    print("\nCore scale metrics:")
    print(pd.Series({
        "cbr_balance_min": df["cbr_eks_balance_bln_rub"].min(),
        "cbr_balance_median": df["cbr_eks_balance_bln_rub"].median(),
        "cbr_balance_max": df["cbr_eks_balance_bln_rub"].max(),
        "cbr_weekly_delta_min": df["cbr_weekly_delta_bln_rub"].min(),
        "cbr_weekly_delta_max": df["cbr_weekly_delta_bln_rub"].max(),
        "roskazna_weekly_delta_min": df["roskazna_weekly_delta_bln_rub"].min(),
        "roskazna_weekly_delta_max": df["roskazna_weekly_delta_bln_rub"].max(),
    }))

    print("\nMissing values, top 12:")
    print(df.isna().sum().sort_values(ascending=False).head(12))

    print("\nFlag_Budget_Drain counts:")
    print(df["Flag_Budget_Drain"].value_counts(dropna=False))
    print(df["Flag_Budget_Drain"].value_counts(normalize=True, dropna=False).rename("share"))

    print("\nSignal reasons:")
    signal_cols = [
        "Flag_CBR_Absolute_Drain",
        "Flag_CBR_Severe_Absolute_Drain",
        "Flag_CBR_MAD_Drain",
        "Flag_Roskazna_Absolute_Deposit_Drop",
        "Flag_Roskazna_MAD_Deposit_Drop",
    ]
    print(df[signal_cols].sum().sort_values(ascending=False))

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
        "Flag_Budget_Drain",
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
# Build dataset
# -----------------------------------------------------------------------------
paths = resolve_paths()
df_raw = load_raw_features(paths["raw_dataset"])
df = build_weekly_timeline(df_raw)
df = apply_cbr_scale_correction(df)
df = calculate_deltas(df)
df = calculate_mad_scores(df)
df = calculate_flags(df)
df = add_ground_truth_features(df)
summary_df = build_feature_summary(df)

print("Input:", paths["raw_dataset"])
print("Output:", paths["processed_dataset"])
print_dataset_report(df)
optional_ground_truth_check(df)

# %%
# Top budget drain rows for manual sanity check.
TOP_COLUMNS = [
    "date",
    "cbr_eks_balance_bln_rub",
    "cbr_weekly_delta_bln_rub",
    "cbr_monthly_delta_bln_rub",
    "MAD_score_CBR",
    "roskazna_deposit_placements_bln_rub",
    "roskazna_weekly_delta_bln_rub",
    "roskazna_monthly_delta_bln_rub",
    "MAD_score_Roskazna",
    "structural_liquidity_balance_bln_rub",
    "Budget_Drain_State",
    "Budget_Drain_Score",
    "Flag_Budget_Drain",
]

df[TOP_COLUMNS].sort_values("Budget_Drain_Score", ascending=False).head(25)

# %%
# Save processed dataset.
paths["processed_dir"].mkdir(parents=True, exist_ok=True)
df.to_csv(paths["processed_dataset"], index=False)
summary_df.to_csv(paths["summary"], index=False)
print(f"Saved feature dataset: {paths['processed_dataset']}")
print(f"Saved feature summary: {paths['summary']}")

# %%
# -----------------------------------------------------------------------------
# EDA plots
# -----------------------------------------------------------------------------
plt.figure(figsize=(14, 6))
plt.plot(df["date"], df["cbr_eks_balance_bln_rub"], label="Остатки бюджетных средств / ЕКС proxy, млрд руб.")
plt.title("Остатки бюджетных средств / ЕКС proxy по времени")
plt.xlabel("Дата")
plt.ylabel("млрд руб.")
plt.legend()
plt.tight_layout()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["date"], df["cbr_weekly_delta_bln_rub"], label="Недельный приток/отток ЦБ/SORS proxy")
plt.axhline(0, linestyle="--", linewidth=1, label="0")
plt.axhline(CBR_ABSOLUTE_DRAIN_THRESHOLD, linestyle="--", linewidth=1, label="Отток -300 млрд")
plt.axhline(CBR_SEVERE_DRAIN_THRESHOLD, linestyle="--", linewidth=1, label="Отток -500 млрд")
alerts = df[df["Flag_CBR_Absolute_Drain"] == 1]
plt.scatter(alerts["date"], alerts["cbr_weekly_delta_bln_rub"], s=24, label="CBR absolute drain")
plt.title("Недельный приток/отток бюджетных средств")
plt.xlabel("Дата")
plt.ylabel("млрд руб.")
plt.legend()
plt.tight_layout()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["date"], df["roskazna_weekly_delta_bln_rub"], label="Недельное изменение размещений Росказны")
plt.axhline(0, linestyle="--", linewidth=1, label="0")
plt.axhline(ROSKAZNA_DEPOSIT_DROP_THRESHOLD, linestyle="--", linewidth=1, label="Падение размещений")
alerts = df[df["Flag_Roskazna_Absolute_Deposit_Drop"] == 1]
plt.scatter(alerts["date"], alerts["roskazna_weekly_delta_bln_rub"], s=24, label="Roskazna drop")
plt.title("Недельное изменение размещений ЕКС на депозитах")
plt.xlabel("Дата")
plt.ylabel("млрд руб.")
plt.legend()
plt.tight_layout()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["date"], df["MAD_score_CBR"], label="MAD-score CBR/SORS proxy")
plt.plot(df["date"], df["MAD_score_Roskazna"], label="MAD-score Roskazna")
plt.axhline(CBR_MAD_DRAIN_THRESHOLD, linestyle="--", linewidth=1, label="MAD drain threshold")
plt.axhline(0, linestyle="--", linewidth=1, label="0")
plt.title("MAD-score бюджетного канала")
plt.xlabel("Дата")
plt.ylabel("MAD-score")
plt.legend()
plt.tight_layout()
plt.show()

# %%
plt.figure(figsize=(10, 5))
state_counts = df["Budget_Drain_State"].value_counts()
plt.bar(state_counts.index.astype(str), state_counts.values)
plt.title("Распределение состояний Budget_Drain_State")
plt.xlabel("Состояние")
plt.ylabel("Количество недель")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.show()

# %%
plt.figure(figsize=(14, 6))
plt.plot(df["date"], df["Budget_Drain_Score"], label="Budget Drain Score")
plt.scatter(
    df.loc[df["Flag_Budget_Drain"] == 1, "date"],
    df.loc[df["Flag_Budget_Drain"] == 1, "Budget_Drain_Score"],
    s=24,
    label="Flag_Budget_Drain",
)
plt.title("Rule-based Budget Drain Score")
plt.xlabel("Дата")
plt.ylabel("Score")
plt.legend()
plt.tight_layout()
plt.show()
