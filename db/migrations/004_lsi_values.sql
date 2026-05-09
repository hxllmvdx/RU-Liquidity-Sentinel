CREATE TABLE IF NOT EXISTS lsi_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    calculation_date DATE NOT NULL UNIQUE,

    lsi DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,

    confidence DOUBLE PRECISION,
    auto_comment TEXT,
    model_version TEXT,

    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_lsi_values_lsi_range
        CHECK (lsi >= 0 AND lsi <= 100),

    CONSTRAINT chk_lsi_values_confidence_range
        CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),

    CONSTRAINT chk_lsi_values_status
        CHECK (status IN ('green', 'yellow', 'red', 'unspecified'))
);

DROP TRIGGER IF EXISTS trg_lsi_values_set_updated_at ON lsi_values;

CREATE TRIGGER trg_lsi_values_set_updated_at
BEFORE UPDATE ON lsi_values
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
