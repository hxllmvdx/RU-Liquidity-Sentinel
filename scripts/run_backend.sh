#!/usr/bin/env bash
set -euo pipefail

cd backend
go run ./cmd/api-gateway
