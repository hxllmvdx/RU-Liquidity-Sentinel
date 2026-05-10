from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any

import pandas as pd


NBSP_RE = re.compile(r"[\u00a0\u202f]")
WS_RE = re.compile(r"\s+")
DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y")
ISSUE_RE = re.compile(r"\b(\d{5}RMFS)\b", re.IGNORECASE)


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = NBSP_RE.sub(" ", str(value)).strip()
    text = WS_RE.sub(" ", text)
    return text or None


def normalize_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = normalize_text(value)
    if not text or text in {"-", "—", "–", "None"}:
        return None
    for token in ("%", "₽", "руб.", "руб", "млрд", "млн.", "млн"):
        text = text.replace(token, "")
    text = text.replace(" ", "").replace(",", ".")
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = normalize_text(value)
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def millions_to_billions(value: Any) -> float | None:
    numeric = normalize_number(value)
    return None if numeric is None else numeric / 1000.0


def calculate_cover_ratio(demand_volume_bln_rub: float | None, offer_volume_bln_rub: float | None) -> float | None:
    if demand_volume_bln_rub is None or offer_volume_bln_rub in (None, 0):
        return None
    return demand_volume_bln_rub / offer_volume_bln_rub


def is_undercovered(cover_ratio: float | None) -> bool:
    return cover_ratio is not None and cover_ratio < 1.2


def is_overcovered(cover_ratio: float | None) -> bool:
    return cover_ratio is not None and cover_ratio > 2.0


def extract_issue(text: str | None) -> str | None:
    if not text:
        return None
    match = ISSUE_RE.search(text)
    return match.group(1).upper() if match else None


@dataclass(slots=True)
class DuplicateCheckResult:
    deduped: pd.DataFrame
    conflicts: pd.DataFrame


def split_duplicates(df: pd.DataFrame) -> DuplicateCheckResult:
    if df.empty:
        return DuplicateCheckResult(df.copy(), df.iloc[0:0].copy())
    keyed = df.copy()
    keyed["_dup_key"] = keyed["auction_date"].astype(str) + "::" + keyed["ofz_issue"].astype(str)
    duplicate_mask = keyed.duplicated("_dup_key", keep=False)
    conflicts = keyed.loc[duplicate_mask].drop(columns="_dup_key").copy()
    deduped = keyed.drop_duplicates("_dup_key", keep="first").drop(columns="_dup_key").copy()
    return DuplicateCheckResult(deduped=deduped, conflicts=conflicts)
