from __future__ import annotations

import json
import logging

from pipeline.history_bootstrap import bootstrap_full_history


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(json.dumps(bootstrap_full_history(), ensure_ascii=False, indent=2, default=str))
