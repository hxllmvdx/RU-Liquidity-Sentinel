from __future__ import annotations

from datetime import date
from typing import Any


def _date_distance_days(left: date, right: date) -> int:
    return abs((left - right).days)


def _weighted_reference_yield(target_days: float, candidates: list[dict[str, Any]]) -> float | None:
    if not candidates:
        return None

    lower = [item for item in candidates if item["_days_to_maturity"] <= target_days]
    upper = [item for item in candidates if item["_days_to_maturity"] >= target_days]

    if lower and upper:
        left = max(lower, key=lambda item: item["_days_to_maturity"])
        right = min(upper, key=lambda item: item["_days_to_maturity"])
        left_days = float(left["_days_to_maturity"])
        right_days = float(right["_days_to_maturity"])
        left_yield = float(left["weighted_avg_yield"])
        right_yield = float(right["weighted_avg_yield"])
        if left_days == right_days:
            return (left_yield + right_yield) / 2.0
        if left_days == target_days:
            return left_yield
        if right_days == target_days:
            return right_yield
        weight = (target_days - left_days) / (right_days - left_days)
        return left_yield + weight * (right_yield - left_yield)

    nearest = sorted(candidates, key=lambda item: abs(float(item["_days_to_maturity"]) - target_days))[:2]
    if not nearest:
        return None
    if len(nearest) == 1:
        return float(nearest[0]["weighted_avg_yield"])
    distances = [max(abs(float(item["_days_to_maturity"]) - target_days), 1.0) for item in nearest]
    weights = [1.0 / distance for distance in distances]
    total_weight = sum(weights)
    return sum(float(item["weighted_avg_yield"]) * weight for item, weight in zip(nearest, weights)) / total_weight


def add_yield_curve_spread(records: list[dict[str, Any]], max_date_distance_days: int = 31, max_maturity_distance_days: int = 3650) -> None:
    eligible = [
        record for record in records
        if record.get("weighted_avg_yield") is not None and record.get("_days_to_maturity") is not None and record.get("auction_date") is not None
    ]
    for record in records:
        record["yield_curve_spread_bp"] = None

    for record in eligible:
        target_date = record["auction_date"]
        target_days = float(record["_days_to_maturity"])
        target_issue = record["ofz_issue"]
        target_yield = float(record["weighted_avg_yield"])

        candidates = []
        for other in eligible:
            if other is record or other["ofz_issue"] == target_issue:
                continue
            if _date_distance_days(target_date, other["auction_date"]) > max_date_distance_days:
                continue
            maturity_gap = abs(float(other["_days_to_maturity"]) - target_days)
            if maturity_gap > max_maturity_distance_days:
                continue
            candidates.append(other)

        if len(candidates) < 2:
            continue

        candidates.sort(key=lambda item: (_date_distance_days(target_date, item["auction_date"]), abs(float(item["_days_to_maturity"]) - target_days)))
        reference_yield = _weighted_reference_yield(target_days, candidates[:8])
        if reference_yield is None:
            continue
        record["yield_curve_spread_bp"] = round((target_yield - reference_yield) * 100.0, 4)


def drop_temporary_fields(records: list[dict[str, Any]]) -> None:
    for record in records:
        record.pop("_days_to_maturity", None)
