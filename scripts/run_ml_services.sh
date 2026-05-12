#!/usr/bin/env bash
set -euo pipefail

cd ml-services

if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python grpc_server/server.py
fi

exec python3 grpc_server/server.py
