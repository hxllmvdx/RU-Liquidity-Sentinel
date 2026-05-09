# RU Liquidity Sentinel

Система раннего предупреждения стресса ликвидности рублевого денежного рынка. MVP-архитектура ориентирована на 5-дневный интенсив, но разложена по production-like сервисам: ingestion/data, ML/analytics, API gateway, frontend dashboard и RAG/LLM analyst.

## Стек

- Backend: Go, gRPC, REST API gateway
- Frontend: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui-ready structure, Apache ECharts
- ML/Data: Python, FastAPI-ready services, pandas, numpy, scipy, scikit-learn, SHAP
- RAG/LLM: Python, PostgreSQL, pgvector
- Storage: PostgreSQL, Redis, raw file storage
- Infra: Docker Compose

## Сервисы

- `backend/` — HTTP gateway, orchestration, scheduler, repositories
- `ml-services/` — ingestion, модули M1-M5, LSI engine, forecast, backtest, scenario, SHAP, RAG/LLM
- `frontend/` — dashboard и исследовательские UI-экраны
- `db/` — migrations и demo seeds
- `proto/` — gRPC contracts между Go backend и Python ML services

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

Локальный запуск по частям:

```bash
make proto
make backend
make ml
make frontend
```

## Redis runtime cache

Backend использует Redis как optional runtime/cache слой, а не как замену PostgreSQL.

- При `REDIS_ENABLED=false` backend продолжает работать без Redis.
- При `REDIS_ENABLED=true` backend делает `PING` Redis на старте и работает в fail-fast режиме, если Redis недоступен.

По умолчанию в Redis кэшируются dashboard/current, latest LSI, modules snapshot, module signals, LSI history и backtest ответы. Distributed lock на recalculation тоже хранится в Redis.
