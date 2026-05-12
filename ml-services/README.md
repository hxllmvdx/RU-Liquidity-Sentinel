# ML Services

Python-контур для ingestion, feature engineering, module signals, MAD-нормализации, LSI, SHAP, forecast, backtest, scenario и RAG/LLM analyst.

## Latest Parsers

По умолчанию production ingestion работает в `latest mode`.

- Каждый parser реализует `fetch_latest()`, `parse_latest()` и `run_latest()`.
- Парсер тянет только свежую страницу или файл, извлекает последние наблюдения и возвращает structured status для orchestration layer.
- Ошибка одного источника не должна останавливать весь pipeline: parser возвращает structured status `success|failed|stale|partial`.

## Database Layer

Файлы:

- [common/database.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/common/database.py)
- [common/db_models.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/common/db_models.py)
- [common/db_errors.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/common/db_errors.py)

Особенности:

- `psycopg 3` sync, без ORM.
- Явные параметризованные SQL-запросы.
- Есть `connect()`, `close()`, `transaction()`, `execute()`, `fetch_one()`, `fetch_all()`, `execute_many()`, `health_check()`.

## Repository Methods

Реализованы repositories:

- `DataSourcesRepository`
- `ModuleSignalsRepository`
- `LSIRepository`
- `ShapRepository`
- `BacktestRepository`
- `RagRepository`

Они инкапсулируют upsert/read методы для PostgreSQL и используются pipeline и gRPC handlers.

## M3/M5 Notebooks Policy

Notebooks:

- [notebooks/03_m3_ofz_feature_analysis.ipynb](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/notebooks/03_m3_ofz_feature_analysis.ipynb)
- [notebooks/05_m5_treasury_feature_analysis.ipynb](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/notebooks/05_m5_treasury_feature_analysis.ipynb)

Политика:

- notebooks только для analysis, feature engineering validation, MAD checks и visualizations;
- production signal logic живёт в `.py`:
  - [modules/m3_ofz/features.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/modules/m3_ofz/features.py)
  - [modules/m3_ofz/signals.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/modules/m3_ofz/signals.py)
  - [modules/m5_treasury/features.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/modules/m5_treasury/features.py)
  - [modules/m5_treasury/signals.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/modules/m5_treasury/signals.py)

## How To Run Latest Recalculation

Из Python:

```python
from pipeline.latest_recalculation import run_latest_recalculation

result = run_latest_recalculation()
print(result)
```

## How gRPC Uses Repositories

Handlers:

- [grpc_server/handlers/lsi_handler.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/grpc_server/handlers/lsi_handler.py)
- [grpc_server/handlers/modules_handler.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/grpc_server/handlers/modules_handler.py)
- [grpc_server/handlers/analyst_handler.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/grpc_server/handlers/analyst_handler.py)
- [grpc_server/handlers/scenario_handler.py](/Users/matvejsamodanov/Documents/ALL/WORK/RU-Liquidity-Sentinel/ml-services/grpc_server/handlers/scenario_handler.py)

Они читают latest LSI, history, module signals и RAG context из PostgreSQL, а `RecalculateLSI` вызывает `run_latest_recalculation()`.

## Environment Variables

- `DATABASE_URL`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_SSLMODE`
- `ML_GRPC_PORT`

## What Is Stored In RAG

В `rag_documents` сохраняются summaries, а не сырые большие файлы:

- LSI history summaries
- module signal summaries
- SHAP top drivers
- backtest conclusions
- tax/calendar events
- module descriptions
- auto-comments
