from __future__ import annotations

from datetime import date, timedelta
import csv
from pathlib import Path

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.roskazna.eks_deposits_parser import EksDepositsParser


class TreasuryParser(BaseParser):
    source_name = "roskazna_treasury"
    source_code = "ROSKAZNA_TREASURY"
    source_url = "https://roskazna.gov.ru/finansovye-operacii/"

    def __init__(self, parser: EksDepositsParser | None = None, db=None) -> None:
        super().__init__(db=db)
        self.parser = parser or EksDepositsParser()

    def fetch_latest(self) -> RawFetchResult:
        date_to = self.utc_now().date()
        date_from = date_to - timedelta(days=7)
        records = self.parser.fetch(date_from, date_to)
        return RawFetchResult(
            source_code=self.source_code,
            url=self.source_url,
            fetched_at=self.utc_now(),
            status=SourceStatus.SUCCESS if records else SourceStatus.STALE,
            content=records,
            metadata={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        )

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        records = list(raw.content or [])
        if not records:
            return []
        latest_date = max(record.observation_date for record in records)
        latest_records = [record for record in records if record.observation_date == latest_date]
        observations: list[RawObservation] = []
        for record in latest_records:
            metrics = [
                ("placement_amount", record.placement_volume_bln_rub, "bln_rub"),
                ("participants_count", float(record.participant_banks_count) if record.participant_banks_count is not None else None, "count"),
                ("delta", None, "bln_rub"),
            ]
            for metric_name, metric_value, unit in metrics:
                observations.append(
                    RawObservation(
                        source_code=self.source_code,
                        observation_date=record.observation_date,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        unit=unit,
                        raw_payload=record.to_dict(),
                    )
                )
        return observations

    def save(self, records, date_from: date, date_to: date, out_dir: Path | None = None) -> Path:
        base_dir = Path(out_dir) if out_dir else self.default_out_dir
        output_path = base_dir / "roskazna" / "treasury" / f"roskazna_treasury_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["observation_date", "placement_volume_bln_rub", "participant_banks_count"])
            writer.writeheader()
            for record in records:
                writer.writerow({
                    "observation_date": record.observation_date.isoformat(),
                    "placement_volume_bln_rub": record.placement_volume_bln_rub,
                    "participant_banks_count": record.participant_banks_count,
                })
        return output_path

    def run_latest(self, out_dir=None) -> ParserRunResult:
        date_to = self.utc_now().date()
        date_from = date_to - timedelta(days=7)
        records = self.parser.fetch(date_from, date_to)
        latest_date = max((record.observation_date for record in records), default=None)
        output_path = self.save(records, date_from, date_to, out_dir=out_dir) if records else None
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if records else SourceStatus.STALE,
            record_count=len(records),
            output_path=output_path,
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )

    def run_historical(self, date_from: date, date_to: date, out_dir=None) -> ParserRunResult:
        records = self.parser.fetch(date_from, date_to)
        latest_date = max((record.observation_date for record in records), default=None)
        output_path = self.save(records, date_from, date_to, out_dir=out_dir) if records else None
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if records else SourceStatus.STALE,
            record_count=len(records),
            output_path=output_path,
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )
