from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from docx import Document
import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import yaml

from ingestion.minfin.ofz_auction_normalizer import (
    calculate_cover_ratio,
    extract_issue,
    is_overcovered,
    is_undercovered,
    millions_to_billions,
    normalize_number,
    normalize_text,
    parse_date,
)
from ingestion.minfin.ofz_auction_source import RawSource


SECTION_CODES = {
    "65": "plans",
    "38": "announcements",
    "39": "results",
    "66": "annual_tables",
}
YEAR_RE = re.compile(r"(20\d{2})")


class MinfinOFZAuctionParser:
    def __init__(self, config_path: Path, raw_dir: Path) -> None:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        self.auction_page_url = config["minfin"]["auction_page"]
        self.timeout_seconds = int(config["minfin"]["timeout_seconds"])
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config["minfin"]["user_agent"]})

    @retry(wait=wait_exponential(multiplier=1, min=1, max=16), stop=stop_after_attempt(5), retry=retry_if_exception_type(requests.RequestException), reraise=True)
    def _get(self, url: str) -> requests.Response:
        response = self.session.get(url, timeout=self.timeout_seconds)
        if response.status_code == 503:
            raise requests.HTTPError("503 from source", response=response)
        response.raise_for_status()
        return response

    def _save_raw(self, content: bytes, filename: str) -> Path:
        path = self.raw_dir / filename
        path.write_bytes(content)
        return path

    def discover_sources(self, year: int | None = None, save_raw: bool = False) -> list[RawSource]:
        first_page = self._get(self.auction_page_url)
        if save_raw:
            self._save_raw(first_page.content, "auction_page_1.html")

        sources: dict[str, RawSource] = {}
        for section_code in SECTION_CODES:
            page = 1
            while True:
                page_url = self.auction_page_url if page == 1 else f"{self.auction_page_url}?page_{section_code}={page}"
                response = first_page if page == 1 else self._get(page_url)
                if page > 1 and save_raw:
                    self._save_raw(response.content, f"auction_page_{section_code}_{page}.html")
                page_sources = self._extract_page_sources(response.text, section_code, year, save_raw)
                added = 0
                for source in page_sources:
                    if source.source_url not in sources:
                        sources[source.source_url] = source
                        added += 1
                if page == 1:
                    total_pages = self._find_total_pages(response.text, section_code)
                if page >= total_pages or added == 0 and page > total_pages:
                    break
                page += 1
        return sorted(sources.values(), key=lambda item: (item.section_code, item.title, item.source_url))

    def _find_total_pages(self, html: str, section_code: str) -> int:
        matches = re.findall(rf"page_{section_code}=(\d+)", html)
        return max([1, *[int(match) for match in matches]])

    def _extract_page_sources(self, html: str, section_code: str, year: int | None, save_raw: bool) -> list[RawSource]:
        soup = BeautifulSoup(html, "lxml")
        section_name = SECTION_CODES[section_code]
        result: list[RawSource] = []
        for card in soup.select(".document_card"):
            title_link = card.select_one(".document_title")
            if title_link is None:
                continue
            title = normalize_text(title_link.get("title") or title_link.get_text(" ", strip=True)) or ""
            if year is not None and str(year) not in title and str(year) not in title_link.get("href", ""):
                file_link = card.select_one(".file_item")
                href_for_year = (file_link.get("href") if file_link else title_link.get("href")) or ""
                if f"_{year}_" not in href_for_year and f"/{year}/" not in href_for_year:
                    continue
            detail_url = urljoin(self.auction_page_url, title_link.get("href"))
            file_link = card.select_one(".file_item")
            href = file_link.get("href") if file_link else title_link.get("href")
            if not href:
                continue
            source_url = urljoin(self.auction_page_url, href)
            lower = source_url.lower()
            if lower.endswith((".xlsx", ".xls")):
                source_type = "excel"
            elif lower.endswith(".docx"):
                source_type = "docx"
            elif lower.endswith(".doc"):
                source_type = "doc"
            elif lower.endswith(".csv"):
                source_type = "csv"
            elif lower.endswith(".json"):
                source_type = "json"
            else:
                source_type = "html"
            content = self._get(source_url).content
            suffix = Path(source_url).suffix or ".html"
            stem = re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:120]
            local_path = self._save_raw(content, f"{section_code}_{source_type}_{stem}{suffix}") if save_raw else self.raw_dir / f"{section_code}_{source_type}_{stem}{suffix}"
            result.append(RawSource(section_code, section_name, source_type, title, detail_url, source_url, content, local_path))
        return result

    def parse_sources(self, sources: list[RawSource]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        records: list[dict[str, Any]] = []
        source_catalog: list[dict[str, Any]] = []
        for source in sources:
            source_catalog.append(
                {
                    "section_code": source.section_code,
                    "section_name": source.section_name,
                    "source_type": source.source_type,
                    "title": source.title,
                    "detail_url": source.detail_url,
                    "source_url": source.source_url,
                    "local_path": str(source.local_path),
                }
            )
            if source.source_type == "excel":
                records.extend(self.parse_excel(source))
            elif source.source_type in {"csv", "json"}:
                records.extend(self.parse_open_data(source))
            elif source.source_type in {"docx", "doc", "html"}:
                records.extend(self.parse_document_like(source))
        return records, source_catalog

    def parse_excel(self, source: RawSource) -> list[dict[str, Any]]:
        frame = pd.read_excel(BytesIO(source.content), header=5)
        frame.columns = [normalize_text(col) for col in frame.columns]
        mapping = {
            "Дата": "auction_date",
            "Формат*": "auction_format",
            "Код выпуска": "ofz_issue",
            "Код  выпуска": "ofz_issue",
            "Тип бумаги**": "security_type",
            "Дата погашения": "maturity_date",
            "Дней до погашения": "days_to_maturity",
            "Объем предложения": "offer_volume_mln_rub",
            "Цена отсечения": "cut_off_price_pct",
            "Цена средневзвешенная": "weighted_avg_price_pct",
            "Доходность по цене отсечения***": "cut_off_yield_pct",
            "Доходность по средневзве- шенной цене***": "weighted_avg_yield",
            "Доходность по средневзвешенной цене***": "weighted_avg_yield",
            "Совокупный объем спроса по номиналу": "demand_volume_mln_rub",
            "Объем размещения по номиналу": "placement_volume_mln_rub",
            "Объем выручки": "revenue_mln_rub",
            "Коэффициент удовлетворения спроса на аукционе": "demand_satisfaction_ratio",
        }
        frame = frame.rename(columns=mapping)
        parsed_at = datetime.now(UTC)
        rows: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            issue = normalize_text(row.get("ofz_issue"))
            auction_date = parse_date(row.get("auction_date"))
            auction_format = normalize_text(row.get("auction_format"))
            if not issue or issue == "Итого" or auction_date is None or issue.isdigit():
                continue
            offer_volume_bln_rub = millions_to_billions(row.get("offer_volume_mln_rub"))
            demand_volume_bln_rub = millions_to_billions(row.get("demand_volume_mln_rub"))
            placement_volume_bln_rub = millions_to_billions(row.get("placement_volume_mln_rub"))
            revenue_bln_rub = millions_to_billions(row.get("revenue_mln_rub"))
            cover_ratio = calculate_cover_ratio(demand_volume_bln_rub, offer_volume_bln_rub)
            rows.append(
                {
                    "auction_date": auction_date,
                    "ofz_issue": issue.replace(" ", "").upper(),
                    "auction_format": auction_format,
                    "security_type": normalize_text(row.get("security_type")),
                    "maturity_date": parse_date(row.get("maturity_date")),
                    "days_to_maturity": normalize_number(row.get("days_to_maturity")),
                    "offer_volume_bln_rub": offer_volume_bln_rub,
                    "demand_volume_bln_rub": demand_volume_bln_rub,
                    "placement_volume_bln_rub": placement_volume_bln_rub,
                    "revenue_bln_rub": revenue_bln_rub,
                    "cover_ratio": cover_ratio,
                    "weighted_avg_yield": normalize_number(row.get("weighted_avg_yield")),
                    "yield_curve_spread_bp": None,
                    "cut_off_price_pct": normalize_number(row.get("cut_off_price_pct")),
                    "weighted_avg_price_pct": normalize_number(row.get("weighted_avg_price_pct")),
                    "cut_off_yield_pct": normalize_number(row.get("cut_off_yield_pct")),
                    "demand_satisfaction_ratio": normalize_number(row.get("demand_satisfaction_ratio")),
                    "is_undercovered": is_undercovered(cover_ratio),
                    "is_overcovered": is_overcovered(cover_ratio),
                    "cbr_confirmed": False,
                    "source_url": source.source_url,
                    "source_detail_url": source.detail_url,
                    "source_type": source.source_type,
                    "source_section": source.section_name,
                    "document_title": source.title,
                    "local_raw_path": str(source.local_path),
                    "cbr_confirmation_url": None,
                    "parsed_at": parsed_at,
                }
            )
        return rows

    def parse_open_data(self, source: RawSource) -> list[dict[str, Any]]:
        if source.source_type == "csv":
            frame = pd.read_csv(BytesIO(source.content))
        else:
            frame = pd.read_json(BytesIO(source.content))
        if frame.empty:
            return []
        frame.columns = [normalize_text(col) for col in frame.columns]
        return self._coerce_generic_frame(frame, source)

    def parse_document_like(self, source: RawSource) -> list[dict[str, Any]]:
        if source.source_type == "docx":
            doc = Document(BytesIO(source.content))
            text = "\n".join(p.text for p in doc.paragraphs if normalize_text(p.text))
        else:
            try:
                text = source.content.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
        html_tables = self._try_html_tables(source)
        if html_tables:
            return html_tables
        return self._parse_text_record(text, source)

    def _try_html_tables(self, source: RawSource) -> list[dict[str, Any]]:
        try:
            tables = pd.read_html(BytesIO(source.content), flavor="lxml")
        except ValueError:
            return []
        all_rows: list[dict[str, Any]] = []
        for table in tables:
            table.columns = [normalize_text(col) for col in table.columns]
            all_rows.extend(self._coerce_generic_frame(table, source))
        return all_rows

    def _coerce_generic_frame(self, frame: pd.DataFrame, source: RawSource) -> list[dict[str, Any]]:
        lower_map = {str(col).lower(): col for col in frame.columns}
        issue_col = next((lower_map[key] for key in lower_map if "выпуск" in key or "код" in key), None)
        date_col = next((lower_map[key] for key in lower_map if "дата" in key), None)
        if not issue_col or not date_col:
            return []
        parsed_at = datetime.now(UTC)
        rows: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            issue = extract_issue(normalize_text(row.get(issue_col)))
            auction_date = parse_date(row.get(date_col))
            if not issue or auction_date is None:
                continue
            offer = millions_to_billions(row.get(next((col for col in frame.columns if "предлож" in str(col).lower()), None)))
            demand = millions_to_billions(row.get(next((col for col in frame.columns if "спрос" in str(col).lower()), None)))
            placement = millions_to_billions(row.get(next((col for col in frame.columns if "размещ" in str(col).lower() and "дополн" not in str(col).lower()), None)))
            revenue = millions_to_billions(row.get(next((col for col in frame.columns if "выруч" in str(col).lower()), None)))
            cover = calculate_cover_ratio(demand, offer)
            rows.append(
                {
                    "auction_date": auction_date,
                    "ofz_issue": issue,
                    "auction_format": normalize_text(row.get(next((col for col in frame.columns if "формат" in str(col).lower()), None))),
                    "security_type": normalize_text(row.get(next((col for col in frame.columns if "тип" in str(col).lower()), None))),
                    "maturity_date": parse_date(row.get(next((col for col in frame.columns if "погаш" in str(col).lower()), None))),
                    "days_to_maturity": normalize_number(row.get(next((col for col in frame.columns if "дней" in str(col).lower()), None))),
                    "offer_volume_bln_rub": offer,
                    "demand_volume_bln_rub": demand,
                    "placement_volume_bln_rub": placement,
                    "revenue_bln_rub": revenue,
                    "cover_ratio": cover,
                    "weighted_avg_yield": normalize_number(row.get(next((col for col in frame.columns if "средневзв" in str(col).lower() and "доход" in str(col).lower()), None))),
                    "yield_curve_spread_bp": None,
                    "cut_off_price_pct": normalize_number(row.get(next((col for col in frame.columns if "цена отсеч" in str(col).lower()), None))),
                    "weighted_avg_price_pct": normalize_number(row.get(next((col for col in frame.columns if "цена средневзв" in str(col).lower()), None))),
                    "cut_off_yield_pct": normalize_number(row.get(next((col for col in frame.columns if "доходность по цене отсеч" in str(col).lower()), None))),
                    "demand_satisfaction_ratio": normalize_number(row.get(next((col for col in frame.columns if "коэффициент удовлетворения" in str(col).lower()), None))),
                    "is_undercovered": is_undercovered(cover),
                    "is_overcovered": is_overcovered(cover),
                    "cbr_confirmed": False,
                    "source_url": source.source_url,
                    "source_detail_url": source.detail_url,
                    "source_type": source.source_type,
                    "source_section": source.section_name,
                    "document_title": source.title,
                    "local_raw_path": str(source.local_path),
                    "cbr_confirmation_url": None,
                    "parsed_at": parsed_at,
                }
            )
        return rows

    def _parse_text_record(self, text: str, source: RawSource) -> list[dict[str, Any]]:
        normalized = normalize_text(text) or ""
        issue = extract_issue(normalized or source.title)
        auction_date = self._extract_russian_date(normalized) or self._extract_russian_date(source.title)
        if not issue or auction_date is None:
            return []
        values = {
            "offer_volume_bln_rub": self._extract_billion_metric(normalized, ["объем предложения"]),
            "demand_volume_bln_rub": self._extract_billion_metric(normalized, ["объем спроса", "совокупный объем спроса"]),
            "placement_volume_bln_rub": self._extract_billion_metric(normalized, ["объем размещения"]),
            "revenue_bln_rub": self._extract_billion_metric(normalized, ["объем выручки"]),
            "weighted_avg_yield": self._extract_percent_metric(normalized, ["средневзвешенная доходность", "доходность по средневзвешенной цене"]),
            "cut_off_yield_pct": self._extract_percent_metric(normalized, ["доходность по цене отсечения"]),
            "cut_off_price_pct": self._extract_percent_metric(normalized, ["цена отсечения"]),
            "weighted_avg_price_pct": self._extract_percent_metric(normalized, ["цена средневзвешенная"]),
        }
        cover = calculate_cover_ratio(values["demand_volume_bln_rub"], values["offer_volume_bln_rub"])
        return [{
            "auction_date": auction_date,
            "ofz_issue": issue,
            "auction_format": "Аукцион" if "дополнительного размещения" not in normalized.lower() else "ДРПА",
            "security_type": None,
            "maturity_date": None,
            "days_to_maturity": None,
            **values,
            "cover_ratio": cover,
            "yield_curve_spread_bp": None,
            "demand_satisfaction_ratio": None,
            "is_undercovered": is_undercovered(cover),
            "is_overcovered": is_overcovered(cover),
            "cbr_confirmed": False,
            "source_url": source.source_url,
            "source_detail_url": source.detail_url,
            "source_type": source.source_type,
            "source_section": source.section_name,
            "document_title": source.title,
            "local_raw_path": str(source.local_path),
            "cbr_confirmation_url": None,
            "parsed_at": datetime.now(UTC),
        }]

    def _extract_russian_date(self, text: str | None) -> datetime.date | None:
        if not text:
            return None
        match = re.search(r"(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(20\d{2})", text, re.IGNORECASE)
        if not match:
            return None
        months = {
            "января": "01", "февраля": "02", "марта": "03", "апреля": "04", "мая": "05", "июня": "06",
            "июля": "07", "августа": "08", "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
        }
        return parse_date(f"{int(match.group(1)):02d}.{months[match.group(2).lower()]}.{match.group(3)}")

    def _extract_billion_metric(self, text: str, labels: list[str]) -> float | None:
        value = self._extract_numeric_after_label(text, labels)
        return None if value is None else value / 1000.0

    def _extract_percent_metric(self, text: str, labels: list[str]) -> float | None:
        return self._extract_numeric_after_label(text, labels)

    def _extract_numeric_after_label(self, text: str, labels: list[str]) -> float | None:
        for label in labels:
            pattern = rf"{label}[^0-9]{{0,40}}([\d\s,.]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return normalize_number(match.group(1))
        return None

    def summarize(self, records: list[dict[str, Any]], sources: list[RawSource]) -> dict[str, Any]:
        years = set()
        for record in records:
            value = record.get("auction_date")
            if not value:
                continue
            parsed = parse_date(value)
            if parsed is not None:
                years.add(parsed.year)
        return {
            "records_total": len(records),
            "sources_total": len(sources),
            "sources_by_type": dict(Counter(source.source_type for source in sources)),
            "sources_by_section": dict(Counter(source.section_name for source in sources)),
            "years_covered": sorted(years),
        }
