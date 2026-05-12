from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from modules.m5_treasury.schema import M5TreasuryFeatureRecord


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


def _maybe_float(value: str | float | None) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def _maybe_int(value: str | int | None) -> int | None:
    if value in (None, "", "None"):
        return None
    return int(float(value))


def _read_csv(path: Path) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _latest_on_or_before(series: dict[date, dict], target_date: date) -> dict | None:
    eligible_dates = [series_date for series_date in series if series_date <= target_date]
    if not eligible_dates:
        return None
    return series[max(eligible_dates)]


def _interpolate_sors_value(sors_by_date: dict[date, dict], target_date: date) -> tuple[float | None, dict | None]:
    if target_date in sors_by_date:
        source = sors_by_date[target_date]
        return _maybe_float(source["value_bln_rub"]), source

    sorted_dates = sorted(sors_by_date)
    previous_dates = [series_date for series_date in sorted_dates if series_date < target_date]
    next_dates = [series_date for series_date in sorted_dates if series_date > target_date]
    if not previous_dates:
        return None, None

    previous_date = previous_dates[-1]
    previous_source = sors_by_date[previous_date]
    previous_value = _maybe_float(previous_source["value_bln_rub"])
    if previous_value is None:
        return None, previous_source

    if not next_dates:
        return previous_value, previous_source

    next_date = next_dates[0]
    next_source = sors_by_date[next_date]
    next_value = _maybe_float(next_source["value_bln_rub"])
    if next_value is None:
        return previous_value, previous_source

    total_days = (next_date - previous_date).days
    elapsed_days = (target_date - previous_date).days
    if total_days <= 0:
        return previous_value, previous_source

    interpolated_value = previous_value + (next_value - previous_value) * (elapsed_days / total_days)
    return interpolated_value, previous_source


def build_features_from_files(sors_path: Path, eks_path: Path, liquidity_path: Path) -> list[M5TreasuryFeatureRecord]:
    sors_records = _read_csv(sors_path)
    eks_records = _read_csv(eks_path)
    liquidity_records = _read_csv(liquidity_path)

    sors_grouped: dict[date, list[dict]] = defaultdict(list)
    for item in sors_records:
        sors_grouped[date.fromisoformat(item["observation_date"])].append(item)
    sors_by_date: dict[date, dict] = {}
    for observation_date, items in sors_grouped.items():
        sors_by_date[observation_date] = {
            "observation_date": observation_date.isoformat(),
            "value_bln_rub": sum(_maybe_float(item["value_bln_rub"]) or 0.0 for item in items),
            "source_file": ",".join(sorted({item["source_file"] for item in items if item.get("source_file")})),
        }

    eks_grouped: dict[date, list[dict]] = defaultdict(list)
    for item in eks_records:
        eks_grouped[date.fromisoformat(item["observation_date"])].append(item)
    eks_by_date: dict[date, dict] = {}
    for observation_date, items in eks_grouped.items():
        eks_by_date[observation_date] = {
            "observation_date": observation_date.isoformat(),
            "placement_volume_bln_rub": sum(_maybe_float(item["placement_volume_bln_rub"]) or 0.0 for item in items),
            "participant_banks_count": max(
                (
                    _maybe_int(item["participant_banks_count"])
                    for item in items
                    if _maybe_int(item["participant_banks_count"]) is not None
                ),
                default=None,
            ),
            "source_file": ",".join(sorted({item["source_file"] for item in items if item.get("source_file")})),
        }

    liquidity_by_date = {
        date.fromisoformat(item["observation_date"]): item
        for item in liquidity_records
    }

    all_dates = sorted(set(sors_by_date) | set(eks_by_date) | set(liquidity_by_date))
    features: list[M5TreasuryFeatureRecord] = []
    balance_by_date: dict[date, float | None] = {}

    for observation_date in all_dates:
        balance, sors = _interpolate_sors_value(sors_by_date, observation_date)
        eks = eks_by_date.get(observation_date)
        latest_liquidity = _latest_on_or_before(liquidity_by_date, observation_date)
        balance_by_date[observation_date] = balance

        history = {d: {"value": v} for d, v in balance_by_date.items() if v is not None}
        week_reference = _latest_on_or_before(history, observation_date - timedelta(days=7))
        month_reference = _latest_on_or_before(history, observation_date - timedelta(days=30))
        delta_week = None if balance is None or week_reference is None else balance - _maybe_float(week_reference["value"])
        delta_month = None if balance is None or month_reference is None else balance - _maybe_float(month_reference["value"])

        features.append(
            M5TreasuryFeatureRecord(
                source_code="M5_TREASURY",
                observation_date=observation_date,
                federal_budget_and_extrabudgetary_funds_balances_bln_rub=balance,
                eks_deposit_placement_volume_bln_rub=_maybe_float(eks["placement_volume_bln_rub"]) if eks else None,
                delta_week_bln_rub=delta_week,
                delta_month_bln_rub=delta_month,
                participant_banks_count=_maybe_int(eks["participant_banks_count"]) if eks else None,
                ground_truth_liquidity_bln_rub=_maybe_float(latest_liquidity["value_bln_rub"]) if latest_liquidity else None,
                raw_refs={
                    "cbr_sors_file": sors["source_file"] if sors else None,
                    "roskazna_file": eks["source_file"] if eks else None,
                    "cbr_liquidity_file": "normalized/cbr_banking_liquidity.csv" if latest_liquidity else None,
                },
                loaded_at=datetime.now(timezone.utc),
            )
        )
    return features
