#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/generate_proto.sh [options]

Options:
  --go-only      Generate only Go stubs
  --python-only  Generate only Python stubs
  --no-clean     Keep previously generated files
  -h, --help     Show this help

Requirements:
  - protoc
  - protoc-gen-go
  - protoc-gen-go-grpc
  - python3
  - python package grpcio-tools
EOF
}

log() {
  printf '[proto] %s\n' "$1"
}

fail() {
  printf '[proto] error: %s\n' "$1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

GENERATE_GO=true
GENERATE_PYTHON=true
CLEAN_OUTPUT=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --go-only)
      GENERATE_GO=true
      GENERATE_PYTHON=false
      ;;
    --python-only)
      GENERATE_GO=false
      GENERATE_PYTHON=true
      ;;
    --no-clean)
      CLEAN_OUTPUT=false
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROTO_ROOT="${REPO_ROOT}/proto"
PROTO_DIR="${PROTO_ROOT}/liquidity/v1"
GO_OUT_DIR="${REPO_ROOT}/backend/gen/go"
PY_OUT_DIR="${REPO_ROOT}/ml-services/gen/python"

[[ -d "${PROTO_DIR}" ]] || fail "proto directory not found: ${PROTO_DIR}"

require_cmd protoc

if [[ "${GENERATE_GO}" == "true" ]]; then
  require_cmd protoc-gen-go
  require_cmd protoc-gen-go-grpc
fi

if [[ "${GENERATE_PYTHON}" == "true" ]]; then
  require_cmd python3
  python3 -m grpc_tools.protoc --version >/dev/null 2>&1 || \
    fail "python module grpc_tools is not installed. Run: pip install grpcio-tools"
fi

PROTO_FILES=(
  "${PROTO_DIR}/common.proto"
  "${PROTO_DIR}/modules.proto"
  "${PROTO_DIR}/lsi.proto"
  "${PROTO_DIR}/scenario.proto"
  "${PROTO_DIR}/backtest.proto"
  "${PROTO_DIR}/analyst.proto"
  "${PROTO_DIR}/liquidity.proto"
)

mkdir -p "${GO_OUT_DIR}" "${PY_OUT_DIR}"

if [[ "${CLEAN_OUTPUT}" == "true" ]]; then
  if [[ "${GENERATE_GO}" == "true" ]]; then
    log "Cleaning Go generated files"
    find "${GO_OUT_DIR}" -type f \( -name '*.pb.go' -o -name '*_grpc.pb.go' \) -delete
  fi
  if [[ "${GENERATE_PYTHON}" == "true" ]]; then
    log "Cleaning Python generated files"
    find "${PY_OUT_DIR}" -type f \( -name '*_pb2.py' -o -name '*_pb2_grpc.py' -o -name '*.pyi' \) -delete
  fi
fi

if [[ "${GENERATE_GO}" == "true" ]]; then
  log "Generating Go protobuf stubs into ${GO_OUT_DIR}"
  protoc \
    -I "${PROTO_ROOT}" \
    --go_out="${GO_OUT_DIR}" \
    --go_opt=paths=source_relative \
    --go-grpc_out="${GO_OUT_DIR}" \
    --go-grpc_opt=paths=source_relative \
    "${PROTO_FILES[@]}"
fi

if [[ "${GENERATE_PYTHON}" == "true" ]]; then
  log "Generating Python protobuf stubs into ${PY_OUT_DIR}"
  python3 -m grpc_tools.protoc \
    -I "${PROTO_ROOT}" \
    --python_out="${PY_OUT_DIR}" \
    --pyi_out="${PY_OUT_DIR}" \
    --grpc_python_out="${PY_OUT_DIR}" \
    "${PROTO_FILES[@]}"
fi

if [[ "${GENERATE_PYTHON}" == "true" ]]; then
  mkdir -p "${PY_OUT_DIR}/liquidity/v1"
  : > "${PY_OUT_DIR}/liquidity/__init__.py"
  : > "${PY_OUT_DIR}/liquidity/v1/__init__.py"
fi

log "Done"
if [[ "${GENERATE_GO}" == "true" ]]; then
  log "Go stubs: ${GO_OUT_DIR}/liquidity/v1"
fi
if [[ "${GENERATE_PYTHON}" == "true" ]]; then
  log "Python stubs: ${PY_OUT_DIR}/liquidity/v1"
fi
