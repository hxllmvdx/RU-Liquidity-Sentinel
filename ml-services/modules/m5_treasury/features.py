from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


AUTO_SCALE_CBR_BALANCE = True
CBR_BALANCE_SCALE_FACTOR = 20.0
CBR_BALANCE_SCALE_IF_MAX_BELOW = 500.0

ROLLING_MAD_WINDOW = 156
ROLLING_MAD_MIN_PERIODS = 24

NUMERIC_RAW_COLS = [
    "federal_budget_and_extrabudgetary_funds_balances_bln_rub",
    "eks_deposit_placement_volume_bln_rub",
    "delta_week_bln_rub",
    "delta_month_bln_rub",
    "participant_banks_count",
    "ground_truth_liquidity_bln_rub",
]


def prepare_m5_treasury_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    for col in NUMERIC_RAW_COLS:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["observation_date"]).sort_values("observation_date")
    return frame.reset_index(drop=True)


def build_weekly_timeline(raw_df: pd.DataFrame) -> pd.DataFrame:
    frame = raw_df.copy()
    frame["week"] = frame["observation_date"].dt.to_period("W-FRI").dt.end_time.dt.normalize()

    agg_spec = {
        "federal_budget_and_extrabudgetary_funds_balances_bln_rub": "last",
        "eks_deposit_placement_volume_bln_rub": "sum",
        "participant_banks_count": "max",
        "ground_truth_liquidity_bln_rub": "last",
    }
    for col in ["source_code", "raw_refs", "loaded_at"]:
        if col in frame.columns:
            agg_spec[col] = "last"

    weekly = frame.groupby("week", as_index=False).agg(agg_spec).rename(columns={"week": "date"})
    weekly = weekly.rename(
        columns={
            "federal_budget_and_extrabudgetary_funds_balances_bln_rub": "cbr_eks_balance_bln_rub",
            "eks_deposit_placement_volume_bln_rub": "roskazna_deposit_placements_bln_rub",
            "ground_truth_liquidity_bln_rub": "structural_liquidity_balance_bln_rub",
        }
    )

    full_weeks = pd.date_range(weekly["date"].min(), weekly["date"].max(), freq="W-FRI")
    weekly = weekly.set_index("date").reindex(full_weeks)
    weekly.index.name = "date"

    for col in ["cbr_eks_balance_bln_rub", "structural_liquidity_balance_bln_rub"]:
        if col in weekly.columns:
            weekly[col] = weekly[col].ffill().bfill()

    weekly["roskazna_deposit_placements_bln_rub"] = weekly["roskazna_deposit_placements_bln_rub"].fillna(0.0)
    for col in ["source_code", "raw_refs", "loaded_at"]:
        if col in weekly.columns:
            weekly[col] = weekly[col].ffill().bfill()

    return weekly.reset_index().sort_values("date").reset_index(drop=True)


def apply_cbr_scale_correction(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["cbr_eks_balance_raw_bln_rub"] = frame["cbr_eks_balance_bln_rub"]
    max_value = frame["cbr_eks_balance_bln_rub"].max(skipna=True)
    scale_factor = 1.0
    if AUTO_SCALE_CBR_BALANCE and pd.notna(max_value) and max_value < CBR_BALANCE_SCALE_IF_MAX_BELOW:
        scale_factor = CBR_BALANCE_SCALE_FACTOR
        frame["cbr_eks_balance_bln_rub"] = frame["cbr_eks_balance_bln_rub"] * scale_factor
    frame["cbr_balance_scale_factor_applied"] = scale_factor
    frame["cbr_balance_scale_note"] = np.where(
        scale_factor != 1.0,
        "scaled_sors_proxy_to_match_m5_threshold_scale",
        "no_scale_correction",
    )
    return frame


def calculate_treasury_deltas(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy().sort_values("date").reset_index(drop=True)
    frame["cbr_weekly_delta_bln_rub"] = frame["cbr_eks_balance_bln_rub"].diff(1)
    frame["cbr_monthly_delta_bln_rub"] = frame["cbr_eks_balance_bln_rub"].diff(4)
    frame["roskazna_weekly_delta_bln_rub"] = frame["roskazna_deposit_placements_bln_rub"].diff(1)
    frame["roskazna_monthly_delta_bln_rub"] = frame["roskazna_deposit_placements_bln_rub"].diff(4)
    frame["delta_week_bln_rub"] = frame["cbr_weekly_delta_bln_rub"]
    frame["delta_month_bln_rub"] = frame["cbr_monthly_delta_bln_rub"]
    return frame


def add_ground_truth_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame["structural_liquidity_weekly_delta_bln_rub"] = frame["structural_liquidity_balance_bln_rub"].diff(1)
    frame["GroundTruth_Liquidity_Deterioration"] = (
        frame["structural_liquidity_weekly_delta_bln_rub"] < 0
    ).fillna(False).astype(int)
    return frame


def build_m5_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = prepare_m5_treasury_dataframe(df)
    frame = build_weekly_timeline(frame)
    frame = apply_cbr_scale_correction(frame)
    frame = calculate_treasury_deltas(frame)
    frame = add_ground_truth_features(frame)
    return frame


def build_features_from_files(sors_path: Path, eks_path: Path, liquidity_path: Path) -> pd.DataFrame:
    del sors_path, eks_path, liquidity_path
    raise NotImplementedError("Legacy CSV builder is deprecated. Use build_m5_features().")
