from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.liquidity_parser import LiquidityParser
from ingestion.cbr.sors_parser import SorsParser
from ingestion.roskazna.eks_deposits_parser import EksDepositsParser
from modules.m5_treasury.features import build_features_from_files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    parser.add_argument("--out-dir", dest="out_dir", default="data/raw")
    args = parser.parse_args()

    date_from = date.fromisoformat(args.date_from) if args.date_from else date(1900, 1, 1)
    date_to = date.fromisoformat(args.date_to) if args.date_to else SorsParser().utc_now().date()
    out_dir = Path(args.out_dir)

    sors_result = SorsParser().run(date_from, date_to, out_dir)
    eks_result = EksDepositsParser().run(date_from, date_to, out_dir)
    liquidity_result = LiquidityParser().run(date_from, date_to, out_dir)

    features = build_features_from_files(sors_result.output_path, eks_result.output_path, liquidity_result.output_path)
    output_path = out_dir / "treasury" / "m5_treasury" / f"m5_treasury_features_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    write_csv_atomic(features, output_path)
    print(output_path)


if __name__ == "__main__":
    main()
