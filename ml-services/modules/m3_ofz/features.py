from __future__ import annotations

import numpy as np
import pandas as pd


COVER_RATIO_CLIP_UPPER = 10.0

NUMERIC_COLS = [
    "offer_volume_bln_rub",
    "demand_volume_bln_rub",
    "placement_volume_bln_rub",
    "cover_ratio",
    "weighted_avg_yield",
    "yield_curve_spread_bp",
]


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")
    result = numerator / denominator.replace(0, np.nan)
    return result.replace([np.inf, -np.inf], np.nan)


def prepare_m3_ofz_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if "issue" in frame.columns and "ofz_issue" not in frame.columns:
        frame["ofz_issue"] = frame["issue"]
    if "offered_amount" in frame.columns and "offer_volume_bln_rub" not in frame.columns:
        frame["offer_volume_bln_rub"] = frame["offered_amount"]
    if "demand_amount" in frame.columns and "demand_volume_bln_rub" not in frame.columns:
        frame["demand_volume_bln_rub"] = frame["demand_amount"]
    if "placed_amount" in frame.columns and "placement_volume_bln_rub" not in frame.columns:
        frame["placement_volume_bln_rub"] = frame["placed_amount"]

    frame["auction_date"] = pd.to_datetime(frame["auction_date"], errors="coerce")
    frame["ofz_issue"] = frame["ofz_issue"].astype(str).str.strip()

    for col in NUMERIC_COLS:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    frame = frame.sort_values("auction_date").reset_index(drop=True)
    frame = frame.drop_duplicates(subset=["auction_date", "ofz_issue"], keep="last")
    return frame.reset_index(drop=True)


def calculate_ofz_cover_ratio(df: pd.DataFrame) -> pd.Series:
    return safe_divide(df["demand_volume_bln_rub"], df["offer_volume_bln_rub"])


def calculate_ofz_yield_spread(df: pd.DataFrame) -> pd.Series:
    if "yield_curve_spread_bp" in df.columns:
        return pd.to_numeric(df["yield_curve_spread_bp"], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def build_m3_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = prepare_m3_ofz_dataframe(df)

    frame["cover_ratio"] = calculate_ofz_cover_ratio(frame)
    frame["cover_ratio_clipped"] = frame["cover_ratio"].clip(upper=COVER_RATIO_CLIP_UPPER)

    frame["placement_to_offer_ratio"] = safe_divide(
        frame["placement_volume_bln_rub"],
        frame["offer_volume_bln_rub"],
    )
    frame["placement_to_demand_ratio"] = safe_divide(
        frame["placement_volume_bln_rub"],
        frame["demand_volume_bln_rub"],
    )

    frame["year"] = frame["auction_date"].dt.year
    frame["month"] = frame["auction_date"].dt.month
    frame["quarter"] = frame["auction_date"].dt.quarter
    frame["day_of_week"] = frame["auction_date"].dt.dayofweek
    frame["ofz_prefix"] = frame["ofz_issue"].str[:2]
    frame["ofz_series"] = frame["ofz_issue"].str[:5]

    shifted_cover = frame["cover_ratio_clipped"].shift(1)
    frame["cover_ratio_roll5_mean"] = shifted_cover.rolling(window=5, min_periods=1).mean()
    frame["cover_ratio_roll5_median"] = shifted_cover.rolling(window=5, min_periods=1).median()
    frame["cover_ratio_roll5_std"] = shifted_cover.rolling(window=5, min_periods=2).std()

    frame["yield_spread"] = calculate_ofz_yield_spread(frame)
    return frame
