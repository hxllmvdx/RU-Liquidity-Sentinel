CREATE TABLE IF NOT EXISTS module_signals (
    id BIGSERIAL PRIMARY KEY,
    module_code TEXT NOT NULL,
    signal_date DATE NOT NULL,
    raw_value DOUBLE PRECISION NOT NULL,
    normalized_value DOUBLE PRECISION NOT NULL,
    contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
