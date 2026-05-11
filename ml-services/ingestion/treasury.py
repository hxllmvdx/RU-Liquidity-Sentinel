from __future__ import annotations

import argparse
from datetime import date
import logging
from pathlib import Path

from ingestion.roskazna.treasury_parser import TreasuryParser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    parser.add_argument("--out-dir", dest="out_dir", default="../data/raw")
    args = parser.parse_args()

    date_from = (
        date.fromisoformat(args.date_from)
        if args.date_from
        else date(1900, 1, 1)
    )
    date_to = (
        date.fromisoformat(args.date_to)
        if args.date_to
        else TreasuryParser().utc_now().date()
    )
    out_dir = Path(args.out_dir)
    result = TreasuryParser().run(date_from, date_to, out_dir)
    print(result.output_path)


if __name__ == "__main__":
    main()
