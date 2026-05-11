from __future__ import annotations

from datetime import date
import html
import logging
import warnings
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult


warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
LOGGER = logging.getLogger(__name__)


class TaxCalendarParser(BaseParser):
    source_name = "nalog_tax_calendar"
    source_code = "NALOG_CALENDAR"
    source_url = "https://www.nalog.gov.ru/opendata/7707329152-kalendar/"

    def __init__(self, db=None) -> None:
        super().__init__(db=db)
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    @staticmethod
    def _month_number(name: str) -> int | None:
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        return months.get(name.lower())

    def _discover_xml_urls(self) -> list[str]:
        response = self.session.get(self.source_url, timeout=20.0)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        urls: list[str] = []
        seen: set[str] = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "data.nalog.ru/opendata/7707329152-kalendar/data-" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            urls.append(href)
        return urls

    def _fetch_bytes(self, url: str) -> bytes:
        response = self.session.get(url, timeout=20.0)
        response.raise_for_status()
        return response.content

    def fetch_latest(self) -> RawFetchResult:
        urls = self._discover_xml_urls()
        latest_url = urls[0] if urls else self.source_url
        return RawFetchResult(
            self.source_code,
            latest_url,
            self.utc_now(),
            SourceStatus.SUCCESS,
            self._fetch_bytes(latest_url),
        )

    def _parse_xml_bytes(self, xml_bytes: bytes) -> list[RawObservation]:
        try:
            root = ET.fromstring(xml_bytes)
            year_nodes = root.findall("year")
            node_iter = (
                (
                    int(year_node.attrib["index"]),
                    self._month_number(month_node.attrib.get("name", "")),
                    day_node.attrib.get("num"),
                    day_node.attrib.get("type"),
                    day_node.text or "",
                )
                for year_node in year_nodes
                if year_node.attrib.get("index")
                for month_node in year_node.findall("month")
                for day_node in month_node.findall("day")
            )
        except ET.ParseError:
            decoded = xml_bytes.decode("cp1251", errors="ignore")
            soup = BeautifulSoup(decoded, "html.parser")
            node_iter = (
                (
                    int(year_node.get("index")),
                    self._month_number(month_node.get("name", "")),
                    day_node.get("num"),
                    day_node.get("type"),
                    day_node.decode_contents() or "",
                )
                for year_node in soup.find_all("year")
                if year_node.get("index")
                for month_node in year_node.find_all("month", recursive=False)
                for day_node in month_node.find_all("day", recursive=False)
            )

        observations: list[RawObservation] = []
        for year, month, day_raw, day_type, raw_html in node_iter:
            if month is None or day_type != "event" or not day_raw:
                continue
            event_date = date(year, month, int(day_raw))
            decoded_html = raw_html.encode("latin1", errors="ignore").decode("cp1251", errors="ignore")
            summary = BeautifulSoup(html.unescape(decoded_html), "html.parser").get_text(" ", strip=True)
            observations.append(
                RawObservation(
                    source_code=self.source_code,
                    observation_date=event_date,
                    metric_name="tax_event",
                    metric_value=None,
                    unit=None,
                    raw_payload={"date": event_date.isoformat(), "summary": summary},
                )
            )
        return observations

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        content = raw.content if isinstance(raw.content, bytes) else str(raw.content).encode("utf-8")
        return self._parse_xml_bytes(content)

    def run_latest(self, out_dir=None) -> ParserRunResult:
        del out_dir
        observations = self.parse_latest(self.fetch_latest())
        latest_date = max((item.observation_date for item in observations), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if observations else SourceStatus.STALE,
            record_count=len(observations),
            requested_from=latest_date,
            requested_to=latest_date,
            latest_observation_date=latest_date,
        )

    def run_historical(self, date_from: date, date_to: date, out_dir=None) -> ParserRunResult:
        del out_dir
        observations: list[RawObservation] = []
        for url in self._discover_xml_urls():
            try:
                content = self._fetch_bytes(url)
            except requests.RequestException as exc:
                LOGGER.warning("Skipping tax calendar release %s due to request error: %s", url, exc)
                continue
            for item in self._parse_xml_bytes(content):
                if date_from <= item.observation_date <= date_to:
                    observations.append(item)

        # Keep one event row per date+summary even if multiple yearly snapshots overlap.
        deduped: dict[tuple[date, str], RawObservation] = {}
        for item in observations:
            summary = str((item.raw_payload or {}).get("summary", ""))
            deduped[(item.observation_date, summary)] = item

        result_observations = sorted(deduped.values(), key=lambda item: (item.observation_date, str((item.raw_payload or {}).get("summary", ""))))
        latest_date = max((item.observation_date for item in result_observations), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if result_observations else SourceStatus.STALE,
            record_count=len(result_observations),
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )
