from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import sys

from modules.m5_treasury.schema import M5TreasuryFeatureRecord


def _maybe_float(value: str | float | None) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def _maybe_int(value: str | int | None) -> int | None:
    if value in (None, "", "None"):
        return None
    return int(float(value))


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_csv(path: Path) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


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


def build_features(
    sors_records: list[dict],
    eks_records: list[dict],
    liquidity_records: list[dict],
) -> list[M5TreasuryFeatureRecord]:
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

    eks_daily_grouped: dict[date, list[dict]] = defaultdict(list)
    for item in eks_records:
        eks_daily_grouped[date.fromisoformat(item["observation_date"])].append(item)
    eks_by_date: dict[date, dict] = {}
    for observation_date, items in eks_daily_grouped.items():
        eks_by_date[observation_date] = {
            "observation_date": observation_date.isoformat(),
            "placement_volume_bln_rub": sum(_maybe_float(item["placement_volume_bln_rub"]) or 0.0 for item in items),
            "participant_banks_count": max(
                (_maybe_int(item["participant_banks_count"]) for item in items if _maybe_int(item["participant_banks_count"]) is not None),
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

        week_anchor = observation_date - timedelta(days=7)
        month_anchor = observation_date - timedelta(days=30)
        week_reference = _latest_on_or_before({d: {"value": v} for d, v in balance_by_date.items() if v is not None}, week_anchor)
        month_reference = _latest_on_or_before({d: {"value": v} for d, v in balance_by_date.items() if v is not None}, month_anchor)
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


def build_features_from_files(sors_path: Path, eks_path: Path, liquidity_path: Path) -> list[M5TreasuryFeatureRecord]:
    return build_features(_read_csv(sors_path), _read_csv(eks_path), _read_csv(liquidity_path))
