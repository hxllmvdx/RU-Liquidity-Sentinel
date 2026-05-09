# Backend

Go API gateway и orchestration layer. Слой принимает REST-запросы от UI, читает локальные репозитории, использует Redis как optional runtime cache и ходит в ML-сервис по gRPC.

## Redis

Redis используется только как быстрый runtime/cache слой и не заменяет PostgreSQL.

Кэшируются:
- `GET /api/dashboard/current`
- `GET /api/lsi/history`
- `GET /api/modules/snapshot`
- `GET /api/modules/:id/signals`
- `GET /api/backtest`

Также Redis используется для distributed lock на `POST /api/recalculate` и краткоживущего job status cache.

PostgreSQL остаётся source of truth для LSI history, module signals, active flags, contributions, SHAP, backtest results, analyst chat history и recalculation jobs.

Если `REDIS_ENABLED=false`, backend работает без Redis и читает данные из PostgreSQL/gRPC.
Если `REDIS_ENABLED=true`, backend делает `PING` Redis на старте и работает в fail-fast режиме, если Redis недоступен.

TTL по умолчанию:
- dashboard: `90s`
- latest LSI: `180s`
- module snapshot: `180s`
- module signals: `600s`
- LSI history: `300s`
- backtest: `1800s`
- job status: `900s`
- recalculation lock: `900s`

Ключи:
- `ru-liquidity:lsi:latest`
- `ru-liquidity:dashboard:current:shap:{bool}:forecast:{bool}:comment:{bool}`
- `ru-liquidity:modules:snapshot:{date|latest}`
- `ru-liquidity:modules:{module_id}:signals:{date_from}:{date_to}`
- `ru-liquidity:lsi:history:{from}:{to}:{limit}:{offset}`
- `ru-liquidity:backtest:{episode}:{from}:{to}:shap:{bool}:breakdown:{bool}`
- `ru-liquidity:job:{job_id}:status`
- `ru-liquidity:lock:recalculation`

Локально Redis можно поднять через `docker compose up redis` или полным стеком `docker compose up --build`.
