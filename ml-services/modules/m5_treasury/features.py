from __future__ import annotations

import json
import csv
from datetime import date, datetime, timezone
from pathlib import Path

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
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_features(
    sors_records: list[dict],
    eks_records: list[dict],
    liquidity_records: list[dict],
) -> list[M5TreasuryFeatureRecord]:
    sors_by_date = {
        date.fromisoformat(item["observation_date"]): item
        for item in sors_records
    }
    eks_by_date = {
        date.fromisoformat(item["observation_date"]): item
        for item in eks_records
    }
    liquidity_by_date = {
        date.fromisoformat(item["observation_date"]): item
        for item in liquidity_records
    }

    all_dates = sorted(set(sors_by_date) | set(eks_by_date))
    features: list[M5TreasuryFeatureRecord] = []
    previous_month_value: float | None = None

    for observation_date in all_dates:
        sors = sors_by_date.get(observation_date)
        eks = eks_by_date.get(observation_date)
        balance = _maybe_float(sors["value_bln_rub"]) if sors else None
        delta_month = None if balance is None or previous_month_value is None else balance - previous_month_value
        if balance is not None:
            previous_month_value = balance

        latest_liquidity = None
        for liquidity_date in sorted(liquidity_by_date):
            if liquidity_date <= observation_date:
                latest_liquidity = liquidity_by_date[liquidity_date]
            else:
                break

        features.append(
            M5TreasuryFeatureRecord(
                source_code="M5_TREASURY",
                observation_date=observation_date,
                federal_budget_and_extrabudgetary_funds_balances_bln_rub=balance,
                eks_deposit_placement_volume_bln_rub=_maybe_float(eks["placement_volume_bln_rub"]) if eks else None,
                delta_week_bln_rub=None,
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
