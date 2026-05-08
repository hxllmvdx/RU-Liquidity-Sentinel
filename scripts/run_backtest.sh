#!/usr/bin/env bash
set -euo pipefail

cd ml-services
python3 -c "from backtest.backtest_service import run_backtest; print(run_backtest())"
