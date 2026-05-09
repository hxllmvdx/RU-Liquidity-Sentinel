CREATE TABLE IF NOT EXISTS shap_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    lsi_value_id UUID NOT NULL REFERENCES lsi_values(id) ON DELETE CASCADE,

    feature_name TEXT NOT NULL,
    module_id TEXT NOT NULL,

    value DOUBLE PRECISION NOT NULL,
    abs_value DOUBLE PRECISION NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_shap_values_module_id
        CHECK (
            module_id IN (
                'M1_RESERVES',
                'M2_REPO',
                'M3_OFZ',
                'M4_TAX',
                'M5_TREASURY'
            )
        ),

    CONSTRAINT chk_shap_values_abs_value_non_negative
        CHECK (abs_value >= 0),

    CONSTRAINT uq_shap_values_lsi_feature
        UNIQUE (lsi_value_id, feature_name)
);
