CREATE TABLE IF NOT EXISTS module_features (
    id BIGSERIAL PRIMARY KEY,
    module_code TEXT NOT NULL,
    feature_date DATE NOT NULL,
    feature_name TEXT NOT NULL,
    value_numeric DOUBLE PRECISION NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
