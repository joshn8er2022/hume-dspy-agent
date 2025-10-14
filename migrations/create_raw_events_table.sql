-- Migration: Create raw_events table for event sourcing
-- Purpose: Store ALL webhook events as immutable event log
-- Pattern: Webhook → Store raw → Return 200 OK → Process async

CREATE TABLE IF NOT EXISTS raw_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    headers JSONB,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_status TEXT DEFAULT 'pending',
    processing_error TEXT,
    retry_count INT DEFAULT 0,
    
    CONSTRAINT valid_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    CONSTRAINT valid_source CHECK (source IN ('typeform', 'slack', 'vapi', 'a2a', 'calendly', 'sendgrid', 'twilio', 'other'))
);

CREATE INDEX IF NOT EXISTS idx_raw_events_source ON raw_events(source);
CREATE INDEX IF NOT EXISTS idx_raw_events_status ON raw_events(processing_status);
CREATE INDEX IF NOT EXISTS idx_raw_events_received_at ON raw_events(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_events_pending ON raw_events(processing_status, received_at) 
    WHERE processing_status = 'pending';

ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage raw_events" ON raw_events
    FOR ALL USING (auth.role() = 'service_role');

COMMENT ON TABLE raw_events IS 'Immutable event log for all webhook events';
