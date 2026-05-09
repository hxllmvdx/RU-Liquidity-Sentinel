CREATE TABLE IF NOT EXISTS backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    episode TEXT NOT NULL,

    range_from DATE NOT NULL,
    range_to DATE NOT NULL,

    conclusion TEXT,

    metrics JSONB,
    events JSONB,
    lsi_history JSONB,
    average_contributions JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_backtest_results_episode
        CHECK (
            episode IN (
                'december_2014',
                'february_march_2022',
                'august_2023',
                'custom'
            )
        ),

    CONSTRAINT chk_backtest_results_range
        CHECK (range_from <= range_to)
);

CREATE TRIGGER trg_backtest_results_set_updated_at
BEFORE UPDATE ON backtest_results
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
