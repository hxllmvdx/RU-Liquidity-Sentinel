from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.base_parser import BaseParser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all BaseParser historical parsers into data/raw")
    parser.add_argument("--from", dest="date_from", default="2021-01-01", help="Start date, YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", default=None, help="End date, YYYY-MM-DD. Default: today UTC")
    parser.add_argument("--out-dir", default=str(ROOT.parent / "data" / "raw"), help="Output raw directory")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    date_from = date.fromisoformat(args.date_from)
    if not args.date_to or args.date_to == "today":
        date_to = datetime.now(timezone.utc).date()
    else:
        date_to = date.fromisoformat(args.date_to)
    results = BaseParser.run_historical_mode(
        date_from=date_from,
        date_to=date_to,
        db=None,
        out_dir=Path(args.out_dir),
    )
    print(json.dumps([
        {
            "source_code": r.source_code,
            "status": r.status,
            "rows": r.record_count,
            "output_path": str(r.output_path) if r.output_path else None,
            "requested_from": str(r.requested_from) if r.requested_from else None,
            "requested_to": str(r.requested_to) if r.requested_to else None,
            "latest_observation_date": str(r.latest_observation_date) if r.latest_observation_date else None,
            "error": r.error,
        }
        for r in results
    ], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
