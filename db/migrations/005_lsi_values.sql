CREATE TABLE IF NOT EXISTS lsi_values (
    id BIGSERIAL PRIMARY KEY,
    as_of_date DATE NOT NULL UNIQUE,
    lsi_value DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,
    model_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
