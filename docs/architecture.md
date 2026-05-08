# Architecture

- `backend` отвечает за REST gateway, orchestration и интеграцию с `ml-services` по gRPC.
- `ml-services` изолирует data ingestion, feature engineering, LSI, SHAP, forecast, scenario, backtest и RAG.
- `frontend` визуализирует текущий LSI, вклады модулей, историю, симуляции и analyst chat.
- `db` хранит time series, derived signals, SHAP, бэктест и RAG-документы.
