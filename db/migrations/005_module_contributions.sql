CREATE TABLE IF NOT EXISTS module_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    lsi_value_id UUID NOT NULL REFERENCES lsi_values(id) ON DELETE CASCADE,

    module_id TEXT NOT NULL,
    module_name TEXT NOT NULL,

    contribution_value DOUBLE PRECISION NOT NULL,
    contribution_percent DOUBLE PRECISION,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_module_contributions_module_id
        CHECK (
            module_id IN (
                'M1_RESERVES',
                'M2_REPO',
                'M3_OFZ',
                'M4_TAX',
                'M5_TREASURY'
            )
        ),

    CONSTRAINT chk_module_contributions_percent_range
        CHECK (contribution_percent IS NULL OR contribution_percent BETWEEN 0 AND 100),

    CONSTRAINT uq_module_contributions_lsi_module
        UNIQUE (lsi_value_id, module_id)
);
