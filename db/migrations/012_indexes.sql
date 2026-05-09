CREATE INDEX IF NOT EXISTS idx_data_sources_source_code
ON data_sources (source_code);

CREATE INDEX IF NOT EXISTS idx_data_sources_is_active
ON data_sources (is_active);

CREATE INDEX IF NOT EXISTS idx_raw_observations_source_date
ON raw_observations (source_id, observation_date);

CREATE INDEX IF NOT EXISTS idx_raw_observations_metric_date
ON raw_observations (metric_name, observation_date);

CREATE INDEX IF NOT EXISTS idx_raw_observations_observation_date_desc
ON raw_observations (observation_date DESC);

CREATE INDEX IF NOT EXISTS idx_lsi_values_calculation_date_desc
ON lsi_values (calculation_date DESC);

CREATE INDEX IF NOT EXISTS idx_lsi_values_status
ON lsi_values (status);

CREATE INDEX IF NOT EXISTS idx_lsi_values_calculated_at_desc
ON lsi_values (calculated_at DESC);

CREATE INDEX IF NOT EXISTS idx_module_signals_signal_date_desc
ON module_signals (signal_date DESC);

CREATE INDEX IF NOT EXISTS idx_module_signals_module_date_desc
ON module_signals (module_id, signal_date DESC);

CREATE INDEX IF NOT EXISTS idx_module_signals_module_signal_date_desc
ON module_signals (module_id, signal_name, signal_date DESC);

CREATE INDEX IF NOT EXISTS idx_active_flags_flag_date_desc
ON active_flags (flag_date DESC);

CREATE INDEX IF NOT EXISTS idx_active_flags_module_date_desc
ON active_flags (module_id, flag_date DESC);

CREATE INDEX IF NOT EXISTS idx_module_contributions_lsi_value_id
ON module_contributions (lsi_value_id);

CREATE INDEX IF NOT EXISTS idx_module_contributions_module_id
ON module_contributions (module_id);

CREATE INDEX IF NOT EXISTS idx_shap_values_lsi_value_id
ON shap_values (lsi_value_id);

CREATE INDEX IF NOT EXISTS idx_shap_values_lsi_abs_value_desc
ON shap_values (lsi_value_id, abs_value DESC);

CREATE INDEX IF NOT EXISTS idx_shap_values_module_id
ON shap_values (module_id);

CREATE INDEX IF NOT EXISTS idx_backtest_results_episode
ON backtest_results (episode);

CREATE INDEX IF NOT EXISTS idx_backtest_results_range
ON backtest_results (range_from, range_to);

CREATE INDEX IF NOT EXISTS idx_backtest_results_created_at_desc
ON backtest_results (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_recalculation_jobs_status
ON recalculation_jobs (status);

CREATE INDEX IF NOT EXISTS idx_recalculation_jobs_started_at_desc
ON recalculation_jobs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_recalculation_jobs_created_at_desc
ON recalculation_jobs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created_at
ON chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at_desc
ON chat_messages (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_documents_source_type
ON rag_documents (source_type);

CREATE INDEX IF NOT EXISTS idx_rag_documents_source_id
ON rag_documents (source_id);

CREATE INDEX IF NOT EXISTS idx_rag_documents_created_at_desc
ON rag_documents (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_documents_metadata_gin
ON rag_documents USING GIN (metadata);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_extension
        WHERE extname = 'vector'
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'rag_documents'
          AND column_name = 'embedding'
    ) THEN
        EXECUTE '
            CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding_hnsw
            ON rag_documents
            USING hnsw (embedding vector_cosine_ops)
        ';
    END IF;
END
$$;
