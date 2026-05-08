CREATE TABLE IF NOT EXISTS raw_observations (
    id BIGSERIAL PRIMARY KEY,
    source_id BIGINT NOT NULL REFERENCES data_sources(id),
    observation_date DATE NOT NULL,
    series_key TEXT NOT NULL,
    value_numeric DOUBLE PRECISION,
    value_text TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_observations_date ON raw_observations(observation_date);
