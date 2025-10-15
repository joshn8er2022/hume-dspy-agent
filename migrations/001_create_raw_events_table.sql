-- Migration: Create raw_events table for event sourcing
-- Date: 2025-10-15

CREATE TABLE IF NOT EXISTS public.raw_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    headers JSONB,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on status for efficient queries
CREATE INDEX IF NOT EXISTS idx_raw_events_status ON public.raw_events(status);

-- Create index on source for filtering
CREATE INDEX IF NOT EXISTS idx_raw_events_source ON public.raw_events(source);

-- Create index on received_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_raw_events_received_at ON public.raw_events(received_at DESC);

-- Create index on event_type
CREATE INDEX IF NOT EXISTS idx_raw_events_event_type ON public.raw_events(event_type);

-- Add RLS policies (Row Level Security)
ALTER TABLE public.raw_events ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role to do everything
CREATE POLICY "Service role can do everything" ON public.raw_events
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Allow anon to insert (webhook receiving)
CREATE POLICY "Allow anonymous insert" ON public.raw_events
    FOR INSERT
    WITH CHECK (true);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_raw_events_updated_at
    BEFORE UPDATE ON public.raw_events
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Add comment
COMMENT ON TABLE public.raw_events IS 'Event sourcing table for all incoming webhooks (Typeform, Slack, etc.)';
