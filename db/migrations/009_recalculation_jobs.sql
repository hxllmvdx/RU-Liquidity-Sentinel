CREATE TABLE IF NOT EXISTS recalculation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    requested_date DATE,

    status TEXT NOT NULL,

    force_reload_sources BOOLEAN NOT NULL DEFAULT false,
    recalculate_shap BOOLEAN NOT NULL DEFAULT true,
    regenerate_comment BOOLEAN NOT NULL DEFAULT true,

    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,

    error_message TEXT,
    updated_sources JSONB,

    result_lsi_value_id UUID REFERENCES lsi_values(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_recalculation_jobs_status
        CHECK (
            status IN (
                'pending',
                'running',
                'success',
                'failed',
                'cancelled'
            )
        ),

    CONSTRAINT chk_recalculation_jobs_time_order
        CHECK (
            started_at IS NULL
            OR finished_at IS NULL
            OR started_at <= finished_at
        )
);

CREATE TRIGGER trg_recalculation_jobs_set_updated_at
BEFORE UPDATE ON recalculation_jobs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
