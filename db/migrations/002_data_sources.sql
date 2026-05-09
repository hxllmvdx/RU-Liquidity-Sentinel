CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    url TEXT,

    source_type TEXT NOT NULL,
    update_frequency TEXT,

    is_active BOOLEAN NOT NULL DEFAULT true,

    last_loaded_at TIMESTAMPTZ,
    last_status TEXT,
    last_error TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_data_sources_set_updated_at ON data_sources;

CREATE TRIGGER trg_data_sources_set_updated_at
BEFORE UPDATE ON data_sources
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
