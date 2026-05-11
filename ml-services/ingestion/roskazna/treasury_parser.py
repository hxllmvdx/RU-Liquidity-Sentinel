from __future__ import annotations

from datetime import date
import logging
from pathlib import Path

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.liquidity_parser import LiquidityParser
from ingestion.cbr.sors_parser import SorsParser
from ingestion.roskazna.eks_deposits_parser import EksDepositsParser
from modules.m5_treasury.features import build_features_from_files


LOGGER = logging.getLogger(__name__)


class TreasuryParser(BaseParser):
    source_name = "roskazna_treasury"
    source_code = "M5_TREASURY"

    def fetch(self, date_from: date, date_to: date) -> list:
        raise NotImplementedError("Use run() for treasury feature orchestration")

    def run(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        output_root = out_dir or self.default_out_dir
        LOGGER.info("Starting treasury build for %s..%s into %s", date_from.isoformat(), date_to.isoformat(), output_root)

        sors_result = SorsParser().run(date_from, date_to, output_root)
        LOGGER.info("SORS ready: %s records -> %s", sors_result.record_count, sors_result.output_path)
        eks_result = EksDepositsParser().run(date_from, date_to, output_root)
        LOGGER.info("EKS ready: %s records -> %s", eks_result.record_count, eks_result.output_path)
        liquidity_result = LiquidityParser().run(date_from, date_to, output_root)
        LOGGER.info("Liquidity ready: %s records -> %s", liquidity_result.record_count, liquidity_result.output_path)

        features = build_features_from_files(
            sors_result.output_path,
            eks_result.output_path,
            liquidity_result.output_path,
        )
        output_path = (
            output_root
            / "treasury"
            / "m5_treasury"
            / f"m5_treasury_features_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        )
        write_csv_atomic(features, output_path)
        LOGGER.info("Treasury features ready: %s rows -> %s", len(features), output_path)
        return ParserRunResult(self.source_code, len(features), output_path, date_from, date_to)
