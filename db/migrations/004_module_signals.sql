CREATE TABLE IF NOT EXISTS module_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    signal_date DATE NOT NULL,

    module_id TEXT NOT NULL,
    signal_name TEXT NOT NULL,

    raw_value DOUBLE PRECISION,
    mad_score DOUBLE PRECISION,

    flag BOOLEAN NOT NULL DEFAULT false,

    unit TEXT,
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_module_signals_module_id
        CHECK (
            module_id IN (
                'M1_RESERVES',
                'M2_REPO',
                'M3_OFZ',
                'M4_TAX',
                'M5_TREASURY'
            )
        ),

    CONSTRAINT uq_module_signals_module_signal_date
        UNIQUE (module_id, signal_name, signal_date)
);

CREATE TABLE IF NOT EXISTS active_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    flag_date DATE NOT NULL,

    module_id TEXT NOT NULL,
    flag_name TEXT NOT NULL,

    description TEXT,
    severity DOUBLE PRECISION,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_active_flags_module_id
        CHECK (
            module_id IN (
                'M1_RESERVES',
                'M2_REPO',
                'M3_OFZ',
                'M4_TAX',
                'M5_TREASURY'
            )
        ),

    CONSTRAINT chk_active_flags_severity_range
        CHECK (severity IS NULL OR severity BETWEEN 0 AND 1),

    CONSTRAINT uq_active_flags_date_module_name
        UNIQUE (flag_date, module_id, flag_name)
);
