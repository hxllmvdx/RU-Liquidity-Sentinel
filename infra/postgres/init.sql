\set ON_ERROR_STOP on

\echo Applying database migrations from /migrations/files

\ir files/001_init_extensions.sql
\ir files/002_data_sources.sql
\ir files/003_raw_observations.sql
\ir files/004_lsi_values.sql
\ir files/005_module_signals.sql
\ir files/006_module_contributions.sql
\ir files/007_shap_values.sql
\ir files/008_backtest_results.sql
\ir files/009_recalculation_jobs.sql
\ir files/010_analyst_chat.sql
\ir files/011_rag_documents.sql
\ir files/012_indexes.sql
