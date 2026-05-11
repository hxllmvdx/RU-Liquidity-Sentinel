from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from datetime import timedelta
import json
import logging
from pathlib import Path
import re
from urllib.parse import quote
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.utils import convert_to_bln_rub, parse_russian_date, parse_russian_float, parse_russian_int
from ingestion.roskazna.client import RoskaznaClient, RoskaznaClientError
from ingestion.roskazna.schemas import RoskaznaEksDepositRecord


LOGGER = logging.getLogger(__name__)
PAGE_URL = (
    "https://roskazna.gov.ru/finansovye-operacii/razmeshchenie-sredstv-edinogo-kaznachejskogo-scheta/"
    "razmeshchenie-sredstv-edinogo-kaznachejskogo-scheta-na-bankovskih-depozitah"
)
OPERATION_DAY_URL = "https://roskazna.gov.ru/finansovye-operacii/operacionnyj-den/"
DEFAULT_MIN_DATE = date(1900, 1, 1)
OPERATION_DAY_CHUNK_DAYS = 120


class EksDepositsParser(BaseParser):
    source_name = "roskazna_eks_deposits"
    source_code = "ROSKAZNA_EKS_DEPOSITS"

    def __init__(self, client: RoskaznaClient | None = None) -> None:
        self.client = client or RoskaznaClient()
        self._output_root: Path | None = None
        self._use_cache_only = False

    @property
    def source_root(self) -> Path:
        return (self._output_root or self.default_out_dir) / "roskazna" / "eks_deposits"

    @property
    def source_files_dir(self) -> Path:
        return self.source_root / "source_files"

    @property
    def manifest_path(self) -> Path:
        return self.source_root / "manifest.json"

    def fetch(self, date_from: date, date_to: date) -> list[RoskaznaEksDepositRecord]:
        LOGGER.info("Fetching EKS deposits for %s..%s", date_from.isoformat(), date_to.isoformat())
        manifest = self._load_manifest()
        if self._use_cache_only:
            links = self._discover_links_from_manifest(manifest, date_from, date_to)
            LOGGER.info("Using cache-only mode with %s manifest links in range", len(links))
        else:
            html = self.client.get(PAGE_URL)
            links = self.discover_xml_links(html, date_from, date_to)
            LOGGER.info("Discovered %s XML links on current EKS page", len(links))
        records: list[RoskaznaEksDepositRecord] = []
        for observation_date, url in links:
            source_path = self.source_files_dir / Path(urlparse(url).path).name
            LOGGER.info("Processing XML %s for %s", url, observation_date.isoformat())
            content, status_payload = self._download_or_load_cached(url, source_path)
            manifest["entries"][url] = {
                "observation_date": observation_date.isoformat(),
                "source_file": str(source_path),
                **status_payload,
            }
            self._write_manifest(manifest)
            if content is None:
                LOGGER.warning("Skipping XML %s: %s", url, status_payload)
                continue
            records.extend(self.parse_xml(content, observation_date, source_path))
        archive_records = self._fetch_operation_day_archive(date_from, date_to, links)
        records.extend(archive_records)
        LOGGER.info(
            "Collected %s raw EKS records total: %s from XML and %s from archive",
            len(records),
            len(records) - len(archive_records),
            len(archive_records),
        )
        return self._aggregate_by_day(records)

    def _fetch_operation_day_archive(
        self,
        date_from: date,
        date_to: date,
        discovered_xml_links: list[tuple[date, str]],
    ) -> list[RoskaznaEksDepositRecord]:
        if self._use_cache_only:
            return []

        archive_date_to = date_to
        if discovered_xml_links:
            earliest_xml_date = min(observation_date for observation_date, _ in discovered_xml_links)
            archive_date_to = min(date_to, earliest_xml_date - timedelta(days=1))
        if archive_date_to < date_from:
            LOGGER.info("Skipping archive fetch because current XML coverage starts at %s", date_to.isoformat())
            return []

        records: list[RoskaznaEksDepositRecord] = []
        chunk_start = date_from
        chunk_index = 0
        while chunk_start <= archive_date_to:
            chunk_index += 1
            chunk_end = min(chunk_start + timedelta(days=OPERATION_DAY_CHUNK_DAYS - 1), archive_date_to)
            url = f"{OPERATION_DAY_URL}?old={chunk_start.strftime('%d/%m/%Y')}&this={chunk_end.strftime('%d/%m/%Y')}"
            LOGGER.info(
                "Archive chunk %s: requesting %s..%s",
                chunk_index,
                chunk_start.isoformat(),
                chunk_end.isoformat(),
            )
            try:
                xml_text = self._export_operation_day_xml(chunk_start, chunk_end)
            except RoskaznaClientError as exc:
                LOGGER.warning(
                    "Archive chunk %s failed for %s..%s: %s",
                    chunk_index,
                    chunk_start.isoformat(),
                    chunk_end.isoformat(),
                    exc,
                )
                break
            chunk_records = self.parse_operation_day_xml(xml_text, url, expected_from=chunk_start, expected_to=chunk_end)
            LOGGER.info(
                "Archive chunk %s parsed %s records for %s..%s",
                chunk_index,
                len(chunk_records),
                chunk_start.isoformat(),
                chunk_end.isoformat(),
            )
            records.extend(chunk_records)
            chunk_start = chunk_end + timedelta(days=1)
        return records

    def _export_operation_day_xml(self, date_from: date, date_to: date) -> str:
        page_html = self.client.get(OPERATION_DAY_URL)
        csrf_match = re.search(r'data-csrf="([^"]+)"', page_html)
        if csrf_match is None:
            raise RoskaznaClientError("operation-day page does not expose csrf token")

        snapshot = None
        for match in re.finditer(r'wire:snapshot="([^"]+)"[^>]+wire:id="([^"]+)"', page_html):
            candidate = json.loads(self._html_unescape(match.group(1)))
            if candidate.get("memo", {}).get("name") == "operation-day":
                snapshot = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
                break
        if snapshot is None:
            raise RoskaznaClientError("operation-day page does not expose livewire snapshot")

        update_payload = {
            "_token": csrf_match.group(1),
            "components": [
                {
                    "snapshot": snapshot,
                    "updates": {"dateFrom": date_from.isoformat(), "dateTo": date_to.isoformat()},
                    "calls": [
                        {
                            "path": "",
                            "method": "__dispatch",
                            "params": [
                                "update-dates",
                                {"startDate": date_from.isoformat(), "endDate": date_to.isoformat()},
                            ],
                        }
                    ],
                }
            ],
        }
        _, updated_json = self._post_livewire(update_payload)
        updated_snapshot = updated_json["components"][0]["snapshot"]
        export_payload = {
            "_token": csrf_match.group(1),
            "components": [
                {
                    "snapshot": updated_snapshot,
                    "updates": {},
                    "calls": [{"path": "", "method": "exportXml", "params": []}],
                }
            ],
        }
        _, export_json = self._post_livewire(export_payload)
        download = export_json["components"][0].get("effects", {}).get("download") or {}
        content = download.get("content")
        if not content:
            return '<?xml version="1.0"?><OperDay/>'
        import base64
        return base64.b64decode(content).decode("utf-8", errors="replace")

    def _post_livewire(self, payload: dict) -> tuple[bool, dict]:
        try:
            response = self.client.session.post(
                f"{self.client.base_url}/livewire/update",
                json=payload,
                timeout=self.client.timeout,
                verify=self.client.ca_bundle,
            )
            used_insecure_fallback = False
        except Exception:
            response = self.client.session.post(
                f"{self.client.base_url}/livewire/update",
                json=payload,
                timeout=self.client.timeout,
                verify=False,
            )
            used_insecure_fallback = True
        if response.status_code >= 400:
            raise RoskaznaClientError(f"Roskazna livewire returned HTTP {response.status_code}")
        return used_insecure_fallback, response.json()

    @staticmethod
    def _html_unescape(value: str) -> str:
        return (
            value.replace("&quot;", '"')
            .replace("&#039;", "'")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
        )

    def _discover_links_from_manifest(self, manifest: dict, date_from: date, date_to: date) -> list[tuple[date, str]]:
        links: list[tuple[date, str]] = []
        for url, payload in manifest.get("entries", {}).items():
            observation_date = date.fromisoformat(payload["observation_date"])
            if date_from <= observation_date <= date_to:
                links.append((observation_date, url))
        return sorted(links)

    def _download_or_load_cached(self, url: str, source_path: Path) -> tuple[str | None, dict]:
        source_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.exists():
            return source_path.read_text(encoding="utf-8"), {"status": "cached", "used_insecure_fallback": False}
        if self._use_cache_only:
            return None, {"status": "missing_cache", "used_insecure_fallback": False}
        try:
            content, used_insecure_fallback = self.client.get_with_fallback_meta(url)
        except RoskaznaClientError as exc:
            return None, {"status": "failed", "used_insecure_fallback": False, "error": str(exc)}
        source_path.write_text(content, encoding="utf-8")
        return content, {"status": "downloaded", "used_insecure_fallback": used_insecure_fallback}

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {"page_url": PAGE_URL, "entries": {}}

    def _write_manifest(self, manifest: dict) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def discover_xml_links(self, html: str, date_from: date, date_to: date) -> list[tuple[date, str]]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[tuple[date, str]] = []
        seen: set[tuple[date, str]] = set()
        for link in soup.find_all("a", href=True):
            text = " ".join(link.get_text(" ", strip=True).split())
            title = " ".join((link.get("title") or "").split())
            href = link["href"]
            parsed_href = urlparse(href)
            if not parsed_href.path.lower().endswith(".xml"):
                continue
            label = title or text
            match = re.search(r"(\d{2}\.\d{2}\.\d{4})", label)
            if not match:
                continue
            observation_date = parse_russian_date(match.group(1))
            if observation_date is None or not (date_from <= observation_date <= date_to):
                continue
            full_url = href if href.startswith("http") else f"{self.client.base_url}{href}"
            candidate = (observation_date, full_url)
            if candidate in seen:
                continue
            seen.add(candidate)
            links.append(candidate)
        return links

    def parse_xml(self, xml_text: str, observation_date: date, source_path: Path) -> list[RoskaznaEksDepositRecord]:
        root = ET.fromstring(xml_text)
        loaded_at = self.utc_now()
        records: list[RoskaznaEksDepositRecord] = []
        for node in root:
            raw = {self._local_name(child.tag): (child.text or "").strip() for child in node}
            record_observation_date = parse_russian_date(raw.get("aucdate")) or observation_date
            period_from = parse_russian_date(raw.get("firstdate"))
            period_to = parse_russian_date(raw.get("seconddate"))
            settle_mln = parse_russian_float(raw.get("totalsettle"))
            participant_banks_count = int(parse_russian_float(raw.get("crbidders"))) if raw.get("crbidders") else None
            records.append(
                RoskaznaEksDepositRecord(
                    source_code=self.source_code,
                    observation_date=record_observation_date,
                    period_from=period_from,
                    period_to=period_to,
                    placement_volume_bln_rub=convert_to_bln_rub(settle_mln, "млн руб."),
                    participant_banks_count=participant_banks_count,
                    auction_count=1,
                    unit="bln_rub",
                    source_file=str(source_path),
                    raw=raw,
                    loaded_at=loaded_at,
                )
            )
        return records

    def parse_operation_day_html(
        self,
        html: str,
        source_url: str,
        *,
        expected_from: date | None = None,
        expected_to: date | None = None,
    ) -> list[RoskaznaEksDepositRecord]:
        soup = BeautifulSoup(html, "html.parser")
        loaded_at = self.utc_now()
        records: list[RoskaznaEksDepositRecord] = []

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue
            header_cells = [cell.get_text(" ", strip=True) for cell in rows[0].find_all(["th", "td"])]
            if not header_cells or "Дата" not in header_cells[0]:
                continue
            header_dates = [parse_russian_date(cell) for cell in header_cells[2:]]
            for row in rows[1:]:
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
                if len(cells) < 3:
                    continue
                if not cells[0].startswith("Размещено на банковских депозитах"):
                    continue
                for observation_date, raw_value in zip(header_dates, cells[2:]):
                    if observation_date is None:
                        continue
                    if expected_from and observation_date < expected_from:
                        continue
                    if expected_to and observation_date > expected_to:
                        continue
                    value_mln = parse_russian_float(raw_value)
                    if value_mln is None:
                        continue
                    records.append(
                        RoskaznaEksDepositRecord(
                            source_code=self.source_code,
                            observation_date=observation_date,
                            period_from=None,
                            period_to=None,
                            placement_volume_bln_rub=convert_to_bln_rub(value_mln, "млн руб."),
                            participant_banks_count=None,
                            auction_count=1,
                            unit="bln_rub",
                            source_file=source_url,
                            raw={"row_label": cells[0], "value": raw_value, "source": "operation_day_html"},
                            loaded_at=loaded_at,
                        )
                    )
                break
        if (expected_from or expected_to) and not records:
            LOGGER.warning(
                "Operation day page did not yield records inside requested range %s..%s for %s",
                expected_from.isoformat() if expected_from else "?",
                expected_to.isoformat() if expected_to else "?",
                source_url,
            )
        return records

    def parse_operation_day_xml(
        self,
        xml_text: str,
        source_url: str,
        *,
        expected_from: date | None = None,
        expected_to: date | None = None,
    ) -> list[RoskaznaEksDepositRecord]:
        root = ET.fromstring(xml_text)
        loaded_at = self.utc_now()
        records: list[RoskaznaEksDepositRecord] = []
        for node in root.findall(".//Rec"):
            oper_date_raw = (node.findtext("OperDate") or "").strip()
            observation_date = date.fromisoformat(oper_date_raw) if oper_date_raw else None
            if observation_date is None:
                observation_date = parse_russian_date(oper_date_raw)
            if observation_date is None:
                continue
            if expected_from and observation_date < expected_from:
                continue
            if expected_to and observation_date > expected_to:
                continue
            placement_volume_rub = parse_russian_float(node.findtext("DepoSum"))
            participant_banks_count = parse_russian_int(node.findtext("DepoCntOrg"))
            raw = {child.tag: (child.text or "").strip() for child in node}
            records.append(
                RoskaznaEksDepositRecord(
                    source_code=self.source_code,
                    observation_date=observation_date,
                    period_from=None,
                    period_to=None,
                    placement_volume_bln_rub=convert_to_bln_rub(placement_volume_rub, "руб."),
                    participant_banks_count=participant_banks_count,
                    auction_count=1,
                    unit="bln_rub",
                    source_file=source_url,
                    raw=raw,
                    loaded_at=loaded_at,
                )
            )
        if (expected_from or expected_to) and not records:
            LOGGER.warning(
                "Operation day XML did not yield records inside requested range %s..%s for %s",
                expected_from.isoformat() if expected_from else "?",
                expected_to.isoformat() if expected_to else "?",
                source_url,
            )
        return records

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.split("}", 1)[-1] if "}" in tag else tag

    def _aggregate_by_day(self, records: list[RoskaznaEksDepositRecord]) -> list[RoskaznaEksDepositRecord]:
        grouped: dict[date, list[RoskaznaEksDepositRecord]] = defaultdict(list)
        for record in records:
            grouped[record.observation_date].append(record)
        aggregated: list[RoskaznaEksDepositRecord] = []
        for observation_date in sorted(grouped):
            day_records = grouped[observation_date]
            aggregated.append(
                RoskaznaEksDepositRecord(
                    source_code=self.source_code,
                    observation_date=observation_date,
                    period_from=min((r.period_from for r in day_records if r.period_from), default=None),
                    period_to=max((r.period_to for r in day_records if r.period_to), default=None),
                    placement_volume_bln_rub=sum(r.placement_volume_bln_rub or 0 for r in day_records),
                    participant_banks_count=max((r.participant_banks_count for r in day_records if r.participant_banks_count is not None), default=None),
                    auction_count=sum(r.auction_count or 0 for r in day_records),
                    unit="bln_rub",
                    source_file=",".join(r.source_file for r in day_records),
                    raw={"original_fields": [r.raw for r in day_records]},
                    loaded_at=day_records[0].loaded_at,
                )
            )
        return aggregated

    def run(self, date_from: date, date_to: date, out_dir: Path | None = None, *, use_cache_only: bool = False) -> ParserRunResult:
        output_root = out_dir or self.default_out_dir
        self._output_root = output_root
        self._use_cache_only = use_cache_only
        records = self.fetch(date_from, date_to)
        output_path = output_root / "roskazna" / "eks_deposits" / "normalized" / f"roskazna_eks_deposits_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        write_csv_atomic(records, output_path)
        LOGGER.info("Wrote %s aggregated EKS rows -> %s", len(records), output_path)
        latest_date = max((record.observation_date for record in records), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status="success",
            record_count=len(records),
            output_path=output_path,
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    parser.add_argument("--out-dir", dest="out_dir", default="data/raw")
    parser.add_argument("--use-cache-only", action="store_true")
    args = parser.parse_args()
    instance = EksDepositsParser()
    date_from = date.fromisoformat(args.date_from) if args.date_from else DEFAULT_MIN_DATE
    date_to = date.fromisoformat(args.date_to) if args.date_to else instance.utc_now().date()
    result = instance.run(date_from, date_to, Path(args.out_dir), use_cache_only=args.use_cache_only)
    print(result.output_path)


if __name__ == "__main__":
    main()
