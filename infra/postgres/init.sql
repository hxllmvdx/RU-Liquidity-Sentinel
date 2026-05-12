\set ON_ERROR_STOP on

\echo Applying database migrations from /migrations/files

\ir files/001_init_extensions.sql
\ir files/002_data_sources.sql
\ir files/003_lsi_values.sql
\ir files/004_module_signals.sql
\ir files/005_module_contributions.sql
\ir files/006_shap_values.sql
\ir files/007_backtest_results.sql
\ir files/008_recalculation_jobs.sql
\ir files/009_analyst_chat.sql
\ir files/010_rag_documents.sql
\ir files/011_indexes.sql
\ir files/012_drop_raw_observations.sql
\ir files/013_remove_demo_seed_rows.sql
