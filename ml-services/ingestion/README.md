# Ingestion

Парсеры публичных источников. Каждый источник изолирован в своей папке, чтобы можно было независимо реализовывать и тестировать загрузку.

## CBR parsers

Доступны парсеры:
- `ingestion.cbr.keyrate_parser`
- `ingestion.cbr.repo_parser`

Оба парсера:
- ходят в CBR по обычному HTTP;
- поддерживают `--from YYYY-MM-DD` и `--to YYYY-MM-DD`;
- пишут raw/normalized артефакты в `data/raw`;
- не используют PostgreSQL и Redis.

Примеры запуска:

```bash
cd ml-services
python -m ingestion.cbr.keyrate_parser --from 2026-05-01 --to 2026-05-08 --out-dir ../data/raw
python -m ingestion.cbr.repo_parser --from 2026-05-01 --to 2026-05-08 --out-dir ../data/raw
```

Формат output:
- `../data/raw/cbr/keyrate/cbr_keyrate_YYYY-MM-DD_YYYY-MM-DD.jsonl`
- `../data/raw/cbr/repo/cbr_repo_YYYY-MM-DD_YYYY-MM-DD.jsonl`
