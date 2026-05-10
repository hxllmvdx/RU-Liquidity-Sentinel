from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from loguru import logger
import yaml

from ingestion.base_parser import BaseParser
from ingestion.minfin.cbr_press_release_checker import CBRPressReleaseChecker
from ingestion.minfin.ofz_auction_exporter import export_outputs
from ingestion.minfin.ofz_auction_normalizer import split_duplicates
from ingestion.minfin.ofz_auction_parser import MinfinOFZAuctionParser
from ingestion.minfin.ofz_auction_validation import validate_records


class OFZParser(BaseParser):
    source_name = "minfin_ofz"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--output", type=Path, default=Path("../data/processed/ofz_auction_results.csv"))
    parser.add_argument("--with-cbr-check", action="store_true")
    parser.add_argument("--save-raw", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    package_dir = Path(__file__).resolve().parent
    ml_root = package_dir.parents[1]
    output_csv = args.output if args.output.is_absolute() else (ml_root / args.output).resolve()
    raw_dir = ml_root.parent / "data" / "raw" / "minfin" / "ofz_auctions"
    config_path = package_dir / "sources.yaml"

    parser = MinfinOFZAuctionParser(config_path=config_path, raw_dir=raw_dir)
    sources = parser.discover_sources(year=args.year, save_raw=args.save_raw)
    records, source_catalog = parser.parse_sources(sources)

    cbr_catalog: list[dict] = []
    if args.with_cbr_check:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        checker = CBRPressReleaseChecker(
            search_url=config["cbr"]["search_url"],
            timeout_seconds=int(config["cbr"]["timeout_seconds"]),
            user_agent=config["cbr"]["user_agent"],
        )
        for record in records:
            confirmation = checker.confirm(record["auction_date"], record["ofz_issue"])
            record["cbr_confirmed"] = confirmation.confirmed
            record["cbr_confirmation_url"] = confirmation.confirmation_url
            record["cbr_confirmation_title"] = confirmation.matched_title
            cbr_catalog.extend(confirmation.matches)

    dedupe = split_duplicates(pd.DataFrame(records))
    validated = validate_records(dedupe.deduped.to_dict(orient="records"))
    summary = parser.summarize(validated, sources)
    report = {
        "requested_year": args.year,
        "min_history_year": 2015,
        "records_parsed": len(records),
        "records_validated": len(validated),
        "duplicates_detected": int(len(dedupe.conflicts)),
        "summary": summary,
        "output_csv": str(output_csv),
    }
    export_outputs(validated, output_csv, dedupe.conflicts, report, source_catalog, cbr_catalog)
    logger.info("Saved {} records from {} sources to {}", len(validated), len(sources), output_csv)


if __name__ == "__main__":
    main()
