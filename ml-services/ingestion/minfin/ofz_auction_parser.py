from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import yaml

from ingestion.minfin.ofz_auction_normalizer import (
    calculate_cover_ratio,
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
MIN_HISTORY_YEAR = 2015
ANNUAL_SECTION_CODE = "66"
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
        for section_code in (ANNUAL_SECTION_CODE,):
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
            detail_url = urljoin(self.auction_page_url, title_link.get("href"))
            file_link = card.select_one(".file_item")
            href = file_link.get("href") if file_link else title_link.get("href")
            if not href:
                continue
            source_url = urljoin(self.auction_page_url, href)
            source_year = self._extract_source_year(title, source_url)
            if source_year is None or source_year < MIN_HISTORY_YEAR:
                continue
            if year is not None and source_year != year:
                continue
            lower = source_url.lower()
            if lower.endswith((".xlsx", ".xls")):
                source_type = "excel"
            else:
                continue
            content = self._get(source_url).content
            suffix = Path(source_url).suffix or ".html"
            stem = re.sub(r"[^A-Za-z0-9._-]+", "_", title)[:120]
            local_path = self._save_raw(content, f"{section_code}_{source_type}_{stem}{suffix}") if save_raw else self.raw_dir / f"{section_code}_{source_type}_{stem}{suffix}"
            result.append(RawSource(section_code, section_name, source_type, title, detail_url, source_url, content, local_path))
        return result

    def _extract_source_year(self, title: str, source_url: str) -> int | None:
        for value in (title, source_url):
            match = YEAR_RE.search(value)
            if match:
                return int(match.group(1))
        return None

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
        return records, source_catalog

    def parse_excel(self, source: RawSource) -> list[dict[str, Any]]:
        frame = pd.read_excel(BytesIO(source.content), header=5)
        frame.columns = [normalize_text(col) for col in frame.columns]
        mapping = {
            "Дата": "auction_date",
            "Дата аукциона": "auction_date",
            "Формат*": "auction_format",
            "Код выпуска": "ofz_issue",
            "Код  выпуска": "ofz_issue",
            "Тип бумаги**": "security_type",
            "Тип бумаги*": "security_type",
            "Дата погашения": "maturity_date",
            "Дней до погашения": "days_to_maturity",
            "Объем предложения": "offer_volume_mln_rub",
            "Цена отсечения": "cut_off_price_pct",
            "Цена средневзвешенная": "weighted_avg_price_pct",
            "Доходность по цене отсечения": "cut_off_yield_pct",
            "Доходность по цене отсечения*": "cut_off_yield_pct",
            "Доходность по цене отсечения**": "cut_off_yield_pct",
            "Доходность по цене отсечения***": "cut_off_yield_pct",
            "Доходность по средневзве- шенной цене": "weighted_avg_yield",
            "Доходность по средневзве- шенной цене*": "weighted_avg_yield",
            "Доходность по средневзве- шенной цене**": "weighted_avg_yield",
            "Доходность по средневзве- шенной цене***": "weighted_avg_yield",
            "Доходность по средневзвешенной цене": "weighted_avg_yield",
            "Доходность по средневзвешенной цене*": "weighted_avg_yield",
            "Доходность по средневзвешенной цене**": "weighted_avg_yield",
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
            normalized_issue = issue.replace(" ", "").upper() if issue else None
            if not issue or issue == "Итого" or auction_date is None or issue.isdigit():
                continue
            if normalized_issue == "ДРПА" or (auction_format and auction_format.lower() != "аукцион"):
                continue
            offer_volume_bln_rub = millions_to_billions(row.get("offer_volume_mln_rub"))
            demand_volume_bln_rub = millions_to_billions(row.get("demand_volume_mln_rub"))
            placement_volume_bln_rub = millions_to_billions(row.get("placement_volume_mln_rub"))
            cover_ratio = calculate_cover_ratio(demand_volume_bln_rub, offer_volume_bln_rub)
            rows.append(
                {
                    "auction_date": auction_date,
                    "ofz_issue": normalized_issue,
                    "_days_to_maturity": normalize_number(row.get("days_to_maturity")),
                    "offer_volume_bln_rub": offer_volume_bln_rub,
                    "demand_volume_bln_rub": demand_volume_bln_rub,
                    "placement_volume_bln_rub": placement_volume_bln_rub,
                    "cover_ratio": cover_ratio,
                    "weighted_avg_yield": normalize_number(row.get("weighted_avg_yield")),
                    "yield_curve_spread_bp": None,
                    "is_undercovered": is_undercovered(cover_ratio),
                    "is_overcovered": is_overcovered(cover_ratio),
                    "cbr_confirmed": False,
                    "source_url": source.source_url,
                    "cbr_confirmation_url": None,
                    "parsed_at": parsed_at,
                }
            )
        return rows

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
