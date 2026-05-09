CREATE TABLE IF NOT EXISTS raw_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,

    observation_date DATE NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    unit TEXT,

    raw_payload JSONB,

    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_raw_observations_source_date_metric
        UNIQUE (source_id, observation_date, metric_name)
);
