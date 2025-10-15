-- Migration: Create leads table for qualified leads
-- Date: 2025-10-15

CREATE TABLE IF NOT EXISTS public.leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    typeform_id TEXT NOT NULL UNIQUE,
    form_id TEXT NOT NULL,

    -- Contact Information
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    company TEXT,

    -- Qualification Results
    qualification_score INTEGER,
    qualification_tier TEXT,
    qualification_reasoning TEXT,
    recommended_actions JSONB,

    -- Agent State
    status TEXT DEFAULT 'new',
    follow_up_count INTEGER DEFAULT 0,
    last_follow_up_at TIMESTAMPTZ,
    response_received BOOLEAN DEFAULT false,
    escalated BOOLEAN DEFAULT false,

    -- Slack Integration
    slack_thread_ts TEXT,
    slack_channel TEXT,

    -- Raw Data
    raw_answers JSONB,
    raw_metadata JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_email ON public.leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_typeform_id ON public.leads(typeform_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_qualification_tier ON public.leads(qualification_tier);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_slack_thread ON public.leads(slack_thread_ts) WHERE slack_thread_ts IS NOT NULL;

-- RLS Policies
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can do everything" ON public.leads
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Allow anonymous insert" ON public.leads
    FOR INSERT
    WITH CHECK (true);

-- Updated_at trigger
CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON public.leads
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

COMMENT ON TABLE public.leads IS 'Qualified leads from Typeform with AI scoring and autonomous follow-up tracking';
