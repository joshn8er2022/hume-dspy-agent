
    CREATE TABLE IF NOT EXISTS processing_failures (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_id TEXT,
        stage TEXT NOT NULL,
        error TEXT NOT NULL,
        traceback TEXT,
        lead_email TEXT,
        lead_company TEXT,
        timestamp TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_processing_failures_timestamp ON processing_failures(timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_processing_failures_stage ON processing_failures(stage);
    CREATE INDEX IF NOT EXISTS idx_processing_failures_lead_email ON processing_failures(lead_email);
    