from __future__ import annotations

from datetime import date

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.minfin.ofz_auction_parser import MinfinOFZAuctionParser


class OFZParser(BaseParser):
    source_name = "minfin_ofz"
    source_code = "MINFIN_OFZ"
    source_url = "https://minfin.gov.ru/ru/perfomance/public_debt/internal/operations/"

    def __init__(self, db=None) -> None:
        super().__init__(db=db)

    def _build_inner_parser(self) -> MinfinOFZAuctionParser:
        from pathlib import Path
        package_dir = Path(__file__).resolve().parent
        config_path = package_dir / "sources.yaml"
        raw_dir = package_dir.parents[3] / "data" / "raw" / "minfin" / "ofz_auctions"
        return MinfinOFZAuctionParser(config_path=config_path, raw_dir=raw_dir)

    def fetch_latest(self) -> RawFetchResult:
        parser = self._build_inner_parser()
        sources = parser.discover_sources(year=self.utc_now().year, save_raw=False)
        latest = sources[-1] if sources else None
        content = latest.model_dump() if hasattr(latest, "model_dump") else latest.__dict__ if latest else {}
        return RawFetchResult(self.source_code, self.source_url, self.utc_now(), SourceStatus.SUCCESS if latest else SourceStatus.STALE, str(content), {"sources_found": len(sources)})

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        parser = self._build_inner_parser()
        sources = parser.discover_sources(year=self.utc_now().year, save_raw=False)
        if not sources:
            return []
        latest_source = [sources[-1]]
        records, _ = parser.parse_sources(latest_source)
        if not records:
            return []
        latest_date = max(date.fromisoformat(item["auction_date"]) for item in records)
        latest_records = [item for item in records if date.fromisoformat(item["auction_date"]) == latest_date]
        observations: list[RawObservation] = []
        for record in latest_records:
            metrics = [
                ("offered_amount", record.get("offer_volume_bln_rub"), "bln_rub"),
                ("demand_amount", record.get("demand_volume_bln_rub"), "bln_rub"),
                ("placed_amount", record.get("placement_volume_bln_rub"), "bln_rub"),
                ("cover_ratio", record.get("cover_ratio"), "ratio"),
                ("weighted_avg_yield", record.get("weighted_avg_yield"), "percent_per_annum"),
            ]
            for metric_name, metric_value, unit in metrics:
                if metric_value is None:
                    continue
                observations.append(
                    RawObservation(
                        source_code=self.source_code,
                        observation_date=latest_date,
                        metric_name=metric_name,
                        metric_value=float(metric_value),
                        unit=unit,
                        raw_payload=record,
                    )
                )
        return observations

    def run_latest(self, out_dir=None) -> ParserRunResult:
        parser = self._build_inner_parser()
        sources = parser.discover_sources(year=self.utc_now().year, save_raw=False)
        if not sources:
            return ParserRunResult(source_code=self.source_code, status=SourceStatus.STALE)
        latest_source = [sources[-1]]
        records, _ = parser.parse_sources(latest_source)
        latest_date = max((date.fromisoformat(item["auction_date"]) for item in records), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if records else SourceStatus.STALE,
            record_count=len(records),
            requested_from=latest_date,
            requested_to=latest_date,
            latest_observation_date=latest_date,
            metadata={"source_count": len(latest_source)},
        )

    def run_historical(self, date_from: date, date_to: date, out_dir=None) -> ParserRunResult:
        del out_dir
        parser = self._build_inner_parser()
        years = range(date_from.year, date_to.year + 1)
        source_count = 0
        record_count = 0
        latest_date = None
        for year in years:
            sources = parser.discover_sources(year=year, save_raw=False)
            filtered = []
            for source in sources:
                source_date = getattr(source, "auction_date", None) or getattr(source, "published_date", None)
                if source_date is None:
                    filtered.append(source)
                    continue
                if date_from <= source_date <= date_to:
                    filtered.append(source)
            if not filtered:
                continue
            records, _ = parser.parse_sources(filtered)
            source_count += len(filtered)
            record_count += len(records)
            if records:
                local_latest = max(date.fromisoformat(item["auction_date"]) for item in records)
                latest_date = max(latest_date, local_latest) if latest_date else local_latest
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if record_count else SourceStatus.STALE,
            record_count=record_count,
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
            metadata={"source_count": source_count},
        )
