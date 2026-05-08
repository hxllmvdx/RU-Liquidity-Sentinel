CREATE TABLE IF NOT EXISTS shap_values (
    id BIGSERIAL PRIMARY KEY,
    as_of_date DATE NOT NULL,
    module_code TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    shap_value DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
