from __future__ import annotations

import numpy as np
import pandas as pd

from normalization.mad_normalizer import rolling_mad_score


STRESS_THRESHOLD = 0.60


def detect_nedospros(df: pd.DataFrame, threshold: float = 1.2) -> pd.Series:
    return (pd.to_numeric(df["cover_ratio"], errors="coerce") < threshold).fillna(False)


def detect_perespros(df: pd.DataFrame, threshold: float = 2.0) -> pd.Series:
    return (pd.to_numeric(df["cover_ratio"], errors="coerce") > threshold).fillna(False)


def calculate_m3_signals(features_df: pd.DataFrame, mad_window: str = "3Y") -> pd.DataFrame:
    del mad_window
    frame = features_df.copy()

    frame["MAD_score_cover"] = rolling_mad_score(frame["cover_ratio_clipped"], window="3Y")
    if "yield_spread" in frame.columns and frame["yield_spread"].notna().sum() > 30:
        frame["MAD_score_yield_spread"] = rolling_mad_score(frame["yield_spread"], window="3Y")
    else:
        frame["MAD_score_yield_spread"] = np.nan

    frame["Flag_Nedospros"] = detect_nedospros(frame).astype(int)
    frame["Flag_Perespros"] = detect_perespros(frame).astype(int)
    frame["Flag_Placement_Stress"] = (
        (frame["placement_to_offer_ratio"] < 0.5) & (frame["cover_ratio"] < 1.5)
    ).astype(int)
    frame["Flag_Low_Cover_MAD"] = (frame["MAD_score_cover"] < -2).astype(int)
    frame["Flag_Extreme_Oversubscription"] = (frame["cover_ratio"] > 5.0).astype(int)

    frame["weak_cover_score"] = np.select(
        condlist=[frame["cover_ratio"] < 1.0, frame["cover_ratio"] < 1.2, frame["cover_ratio"] < 1.5],
        choicelist=[1.0, 0.8, 0.4],
        default=0.0,
    )
    frame["weak_placement_score"] = np.select(
        condlist=[
            (frame["placement_to_offer_ratio"] < 0.3) & (frame["cover_ratio"] < 1.5),
            (frame["placement_to_offer_ratio"] < 0.5) & (frame["cover_ratio"] < 1.5),
            (frame["placement_to_offer_ratio"] < 0.8) & (frame["cover_ratio"] < 1.2),
        ],
        choicelist=[1.0, 0.7, 0.4],
        default=0.0,
    )
    frame["mad_cover_score"] = np.select(
        condlist=[frame["MAD_score_cover"] < -3, frame["MAD_score_cover"] < -2, frame["MAD_score_cover"] < -1],
        choicelist=[1.0, 0.7, 0.3],
        default=0.0,
    )

    if frame["MAD_score_yield_spread"].notna().sum() > 0:
        frame["yield_spread_score"] = np.select(
            condlist=[
                frame["MAD_score_yield_spread"] > 3,
                frame["MAD_score_yield_spread"] > 2,
                frame["MAD_score_yield_spread"] > 1,
            ],
            choicelist=[1.0, 0.7, 0.3],
            default=0.0,
        )
    else:
        frame["yield_spread_score"] = 0.0

    frame["Stress_Score"] = (
        0.45 * frame["weak_cover_score"]
        + 0.30 * frame["weak_placement_score"]
        + 0.15 * frame["mad_cover_score"]
        + 0.10 * frame["yield_spread_score"]
    )
    frame["Stress_Flag"] = (frame["Stress_Score"] >= STRESS_THRESHOLD).astype(int)
    frame["Stress_Level"] = pd.cut(
        frame["Stress_Score"],
        bins=[-0.01, 0.30, 0.60, 1.00],
        labels=["normal", "warning", "stress"],
    )
    return frame
