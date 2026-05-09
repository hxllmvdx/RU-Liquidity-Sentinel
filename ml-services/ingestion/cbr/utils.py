from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
import re


MOSCOW_TZ = ZoneInfo("Europe/Moscow")
EMPTY_MARKERS = {"", "-", "—", "–", None}


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.replace("\xa0", " ").split())


def parse_russian_float(value: str | None) -> float | None:
    cleaned = clean_text(value)
    if cleaned in EMPTY_MARKERS:
        return None
    normalized = cleaned.replace(" ", "").replace(",", ".")
    return float(normalized)


def parse_russian_int(value: str | None) -> int | None:
    parsed = parse_russian_float(value)
    if parsed is None:
        return None
    return int(parsed)


def parse_russian_date(value: str | None) -> date | None:
    cleaned = clean_text(value)
    if cleaned in EMPTY_MARKERS:
        return None
    return datetime.strptime(cleaned, "%d.%m.%Y").date()


def parse_repo_caption_datetime(value: str | None) -> tuple[date | None, datetime | None]:
    cleaned = clean_text(value)
    if cleaned in EMPTY_MARKERS:
        return None, None

    match = re.search(r"(\d{2}\.\d{2}\.\d{4})(?:\s+на\s+(\d{2}:\d{2}))?", cleaned)
    if not match:
        return None, None

    parsed_date = datetime.strptime(match.group(1), "%d.%m.%Y").date()
    if not match.group(2):
        return parsed_date, None

    parsed_dt = datetime.strptime(
        f"{match.group(1)} {match.group(2)}",
        "%d.%m.%Y %H:%M",
    ).replace(tzinfo=MOSCOW_TZ)
    return parsed_date, parsed_dt
