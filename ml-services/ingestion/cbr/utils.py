from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo
import re


MOSCOW_TZ = ZoneInfo("Europe/Moscow")
EMPTY_MARKERS = {"", "-", "—", "–", "н/д", "Н/Д", None}
RUSSIAN_MONTHS = {
    "январь": 1,
    "января": 1,
    "февраль": 2,
    "февраля": 2,
    "март": 3,
    "марта": 3,
    "апрель": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июль": 7,
    "июля": 7,
    "август": 8,
    "августа": 8,
    "сентябрь": 9,
    "сентября": 9,
    "октябрь": 10,
    "октября": 10,
    "ноябрь": 11,
    "ноября": 11,
    "декабрь": 12,
    "декабря": 12,
}


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
    if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", cleaned):
        return datetime.strptime(cleaned, "%d.%m.%Y").date()

    month_match = re.fullmatch(r"([А-Яа-яёЁ]+)\s+(\d{4})", cleaned)
    if month_match:
        month = RUSSIAN_MONTHS.get(month_match.group(1).lower())
        if month is None:
            return None
        return date(int(month_match.group(2)), month, 1)

    embedded_match = re.search(r"(\d{2}\.\d{2})\.(\d{4})", cleaned)
    if embedded_match:
        return datetime.strptime(
            f"{embedded_match.group(1)}.{embedded_match.group(2)}",
            "%d.%m.%Y",
        ).date()
    return None


def convert_to_bln_rub(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    cleaned_unit = clean_text(unit).lower()
    if "млрд" in cleaned_unit:
        return value
    if "млн" in cleaned_unit:
        return value / 1000
    if "тыс" in cleaned_unit:
        return value / 1_000_000
    if "руб" in cleaned_unit:
        return value / 1_000_000_000
    raise ValueError(f"unsupported unit for RUB conversion: {unit!r}")


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
