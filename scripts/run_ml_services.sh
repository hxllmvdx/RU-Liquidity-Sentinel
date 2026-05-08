#!/usr/bin/env bash
set -euo pipefail

cd ml-services
python3 grpc_server/server.py
