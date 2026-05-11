from __future__ import annotations

import numpy as np
import pandas as pd

from normalization.mad_normalizer import rolling_mad_score


CBR_ABSOLUTE_DRAIN_THRESHOLD = -300.0
CBR_SEVERE_DRAIN_THRESHOLD = -500.0
CBR_MAD_DRAIN_THRESHOLD = -3.5
ROSKAZNA_DEPOSIT_DROP_THRESHOLD = -1500.0
ROSKAZNA_MAD_DROP_THRESHOLD = -3.5


def detect_budget_drain(df: pd.DataFrame, weekly_threshold_bln: float = 300.0, monthly_threshold_bln: float | None = None) -> pd.Series:
    frame = df.copy()
    weekly = pd.to_numeric(frame["cbr_weekly_delta_bln_rub"], errors="coerce")
    drain = (weekly <= -abs(weekly_threshold_bln)).fillna(False)
    if monthly_threshold_bln is not None and "cbr_monthly_delta_bln_rub" in frame.columns:
        monthly = pd.to_numeric(frame["cbr_monthly_delta_bln_rub"], errors="coerce")
        drain = drain | (monthly <= -abs(monthly_threshold_bln)).fillna(False)
    return drain


def calculate_m5_signals(features_df: pd.DataFrame, mad_window: str = "3Y") -> pd.DataFrame:
    del mad_window
    frame = features_df.copy()
    frame["MAD_score_CBR"] = rolling_mad_score(frame["cbr_weekly_delta_bln_rub"], window="3Y")
    frame["MAD_score_Roskazna"] = rolling_mad_score(frame["roskazna_weekly_delta_bln_rub"], window="3Y")

    frame["Flag_CBR_Absolute_Drain"] = (frame["cbr_weekly_delta_bln_rub"] <= CBR_ABSOLUTE_DRAIN_THRESHOLD).fillna(False).astype(int)
    frame["Flag_CBR_Severe_Absolute_Drain"] = (frame["cbr_weekly_delta_bln_rub"] <= CBR_SEVERE_DRAIN_THRESHOLD).fillna(False).astype(int)
    frame["Flag_CBR_MAD_Drain"] = (frame["MAD_score_CBR"] <= CBR_MAD_DRAIN_THRESHOLD).fillna(False).astype(int)
    frame["Flag_Roskazna_Absolute_Deposit_Drop"] = (frame["roskazna_weekly_delta_bln_rub"] <= ROSKAZNA_DEPOSIT_DROP_THRESHOLD).fillna(False).astype(int)
    frame["Flag_Roskazna_MAD_Deposit_Drop"] = (frame["MAD_score_Roskazna"] <= ROSKAZNA_MAD_DROP_THRESHOLD).fillna(False).astype(int)

    flag_cols = [
        "Flag_CBR_Absolute_Drain",
        "Flag_CBR_Severe_Absolute_Drain",
        "Flag_CBR_MAD_Drain",
        "Flag_Roskazna_Absolute_Deposit_Drop",
        "Flag_Roskazna_MAD_Deposit_Drop",
    ]
    frame["Flag_Budget_Drain"] = (frame[flag_cols].sum(axis=1) > 0).astype(int)
    frame["Budget_Drain_State"] = np.select(
        [
            frame[flag_cols].sum(axis=1) > 1,
            frame["Flag_CBR_Severe_Absolute_Drain"] == 1,
            frame["Flag_CBR_Absolute_Drain"] == 1,
            frame["Flag_CBR_MAD_Drain"] == 1,
            frame["Flag_Roskazna_Absolute_Deposit_Drop"] == 1,
            frame["Flag_Roskazna_MAD_Deposit_Drop"] == 1,
        ],
        [
            "combined_budget_drain",
            "cbr_severe_absolute_drain",
            "cbr_absolute_drain",
            "cbr_mad_drain",
            "roskazna_absolute_deposit_drop",
            "roskazna_mad_deposit_drop",
        ],
        default="neutral",
    )
    frame["Budget_Drain_Score"] = (
        0.35 * frame["Flag_CBR_Absolute_Drain"]
        + 0.20 * frame["Flag_CBR_Severe_Absolute_Drain"]
        + 0.20 * frame["Flag_CBR_MAD_Drain"]
        + 0.35 * frame["Flag_Roskazna_Absolute_Deposit_Drop"]
        + 0.15 * frame["Flag_Roskazna_MAD_Deposit_Drop"]
    ).clip(upper=1.0)
    frame["Budget_Drain_Level"] = pd.cut(
        frame["Budget_Drain_Score"],
        bins=[-0.01, 0.01, 0.35, 0.70, 1.00],
        labels=["normal", "watch", "warning", "stress"],
    )
    return frame
