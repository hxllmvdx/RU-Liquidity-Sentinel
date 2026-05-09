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
    parser.add_argument("--from", dest="date_from", default="2019-01-01")
    parser.add_argument("--to", dest="date_to", default="2026-05-01")
    parser.add_argument("--out-dir", dest="out_dir", default="data/raw")
    args = parser.parse_args()

    date_from = date.fromisoformat(args.date_from)
    date_to = date.fromisoformat(args.date_to)
    out_dir = Path(args.out_dir)

    sors_result = SorsParser().run(date_from, date_to, out_dir)
    eks_result = EksDepositsParser().run(max(date(2021, 1, 1), date_from), date_to, out_dir)
    liquidity_result = LiquidityParser().run(max(date(2014, 2, 1), date_from), min(date(2026, 3, 2), date_to), out_dir)

    features = build_features_from_files(sors_result.output_path, eks_result.output_path, liquidity_result.output_path)
    output_path = out_dir / "treasury" / "m5_treasury" / f"m5_treasury_features_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    write_csv_atomic(features, output_path)
    print(output_path)


if __name__ == "__main__":
    main()
