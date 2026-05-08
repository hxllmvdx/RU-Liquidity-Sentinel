SHELL := /bin/bash
.DEFAULT_GOAL := help

PROJECT_NAME := RU Liquidity Sentinel
ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ENV_FILE := $(ROOT_DIR)/.env

COMPOSE := docker compose
COMPOSE_BASE := $(COMPOSE) -f docker-compose.yml
COMPOSE_MACOS := $(COMPOSE) -f docker-compose.yml -f docker-compose.macos.yml
COMPOSE_GPU := $(COMPOSE) -f docker-compose.yml -f docker-compose.gpu.yml

.PHONY: help env-check env-init proto proto-go proto-python backend ml frontend backtest seed \
        compose-up compose-down compose-logs compose-ps \
        compose-up-macos compose-up-gpu \
        fmt lint clean

help: ## Show available commands
	@echo "$(PROJECT_NAME)"
	@echo
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env-check: ## Ensure .env exists
	@if [[ ! -f "$(ENV_FILE)" ]]; then \
		echo "Missing .env. Run 'make env-init' first."; \
		exit 1; \
	fi

env-init: ## Create .env from .env.example if missing
	@if [[ -f "$(ENV_FILE)" ]]; then \
		echo ".env already exists"; \
	else \
		cp "$(ROOT_DIR)/.env.example" "$(ENV_FILE)"; \
		echo "Created .env from .env.example"; \
	fi

proto: ## Generate Go and Python protobuf/gRPC stubs
	bash "$(ROOT_DIR)/scripts/generate_proto.sh"

proto-go: ## Generate only Go protobuf/gRPC stubs
	bash "$(ROOT_DIR)/scripts/generate_proto.sh" --go-only

proto-python: ## Generate only Python protobuf/gRPC stubs
	bash "$(ROOT_DIR)/scripts/generate_proto.sh" --python-only

backend: ## Run Go API gateway locally
	bash "$(ROOT_DIR)/scripts/run_backend.sh"

ml: ## Run Python ML/gRPC service locally
	bash "$(ROOT_DIR)/scripts/run_ml_services.sh"

frontend: ## Run Next.js frontend locally
	bash "$(ROOT_DIR)/scripts/run_frontend.sh"

backtest: ## Run local backtest stub
	bash "$(ROOT_DIR)/scripts/run_backtest.sh"

seed: ## Print seed instructions for demo data
	bash "$(ROOT_DIR)/scripts/seed_demo_data.sh"

compose-up: env-check ## Start local stack with base Docker Compose
	$(COMPOSE_BASE) up --build

compose-down: ## Stop local stack
	$(COMPOSE_BASE) down

compose-logs: ## Tail logs from base Docker Compose stack
	$(COMPOSE_BASE) logs -f

compose-ps: ## Show base Docker Compose services
	$(COMPOSE_BASE) ps

compose-up-macos: env-check ## Start stack with macOS Ollama override
	$(COMPOSE_MACOS) up --build

compose-up-gpu: env-check ## Start stack with Nvidia GPU Ollama override
	$(COMPOSE_GPU) up --build

fmt: ## Run lightweight formatting where tools are available
	@if command -v gofmt >/dev/null 2>&1; then \
		find "$(ROOT_DIR)/backend" -name '*.go' -print0 | xargs -0 gofmt -w; \
	else \
		echo "gofmt not found, skipping Go formatting"; \
	fi
	@if command -v python3 >/dev/null 2>&1; then \
		python3 -m compileall "$(ROOT_DIR)/ml-services" >/dev/null || true; \
	else \
		echo "python3 not found, skipping Python sanity check"; \
	fi

lint: ## Run lightweight repository sanity checks
	@bash -n "$(ROOT_DIR)/scripts/generate_proto.sh"
	@bash -n "$(ROOT_DIR)/scripts/run_backend.sh"
	@bash -n "$(ROOT_DIR)/scripts/run_ml_services.sh"
	@bash -n "$(ROOT_DIR)/scripts/run_frontend.sh"
	@bash -n "$(ROOT_DIR)/scripts/run_backtest.sh"
	@bash -n "$(ROOT_DIR)/scripts/seed_demo_data.sh"
	@protoc -I "$(ROOT_DIR)/proto" --descriptor_set_out=/private/tmp/ru-liquidity-sentinel.pb "$(ROOT_DIR)"/proto/liquidity/v1/*.proto
	@echo "Lint checks passed"

clean: ## Remove generated protobuf artifacts
	@find "$(ROOT_DIR)/backend/gen/go" -type f \( -name '*.pb.go' -o -name '*_grpc.pb.go' \) -delete
	@find "$(ROOT_DIR)/ml-services/gen/python" -type f \( -name '*_pb2.py' -o -name '*_pb2_grpc.py' -o -name '*.pyi' \) -delete 2>/dev/null || true
	@echo "Generated protobuf artifacts removed"
