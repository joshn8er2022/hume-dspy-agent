-- Migration 007: Create Conversations Table for ABM
-- Created: 2025-10-23
-- Purpose: Track conversation state and context for multi-touch campaigns

-- ============================================================================
-- CONVERSATIONS TABLE
-- ============================================================================
-- Tracks ongoing conversations with contacts
-- Maintains context, status, and qualification tier for intelligent engagement

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relationships
    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Conversation Status
    status TEXT NOT NULL DEFAULT 'active',
    -- Status: active, paused, closed, won, lost, nurturing
    
    qualification_tier TEXT,
    -- Tiers: scorching, hot, warm, cool, cold
    
    -- Engagement Tracking
    last_touchpoint_at TIMESTAMPTZ,
    next_touchpoint_at TIMESTAMPTZ,
    touchpoint_count INTEGER DEFAULT 0,
    
    -- Response Tracking
    last_response_at TIMESTAMPTZ,
    response_count INTEGER DEFAULT 0,
    avg_response_time_hours DECIMAL(10,2),
    
    -- Conversation Context
    context JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "topics_discussed": [...],
    --   "pain_points_identified": [...],
    --   "objections_raised": [...],
    --   "interests_expressed": [...],
    --   "next_steps": [...],
    --   "key_quotes": [...],
    --   "sentiment": "positive",
    --   "engagement_level": "high"
    -- }
    
    -- Campaign Info
    campaign_id UUID,  -- Optional: link to specific campaign
    campaign_name TEXT,
    sequence_step INTEGER DEFAULT 0,  -- Current step in sequence
    
    -- Outcome Tracking
    outcome TEXT,  -- meeting_scheduled, demo_requested, not_interested, etc.
    outcome_date TIMESTAMPTZ,
    outcome_notes TEXT,
    
    -- Value Tracking
    estimated_value DECIMAL(10,2),
    actual_value DECIMAL(10,2),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "source": "inbound|outbound",
    --   "initial_channel": "email",
    --   "referral_source": "...",
    --   "utm_params": {...},
    --   "custom_fields": {...}
    -- }
    
    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_conversations_contact_id ON conversations(contact_id);
CREATE INDEX IF NOT EXISTS idx_conversations_company_id ON conversations(company_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_qualification_tier ON conversations(qualification_tier);
CREATE INDEX IF NOT EXISTS idx_conversations_next_touchpoint ON conversations(next_touchpoint_at) 
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_conversations_campaign ON conversations(campaign_id) 
    WHERE campaign_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- GIN indexes for JSONB queries
CREATE INDEX IF NOT EXISTS idx_conversations_context ON conversations USING GIN(context);
CREATE INDEX IF NOT EXISTS idx_conversations_metadata ON conversations USING GIN(metadata);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_conversations_company_status 
    ON conversations(company_id, status);
CREATE INDEX IF NOT EXISTS idx_conversations_contact_status 
    ON conversations(contact_id, status);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_updated_at_trigger
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversations_updated_at();

-- Update company active conversations count
CREATE OR REPLACE FUNCTION update_company_conversation_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status = 'active' THEN
        UPDATE companies 
        SET active_conversations = active_conversations + 1
        WHERE id = NEW.company_id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status = 'active' AND NEW.status != 'active' THEN
            UPDATE companies 
            SET active_conversations = GREATEST(0, active_conversations - 1)
            WHERE id = OLD.company_id;
        ELSIF OLD.status != 'active' AND NEW.status = 'active' THEN
            UPDATE companies 
            SET active_conversations = active_conversations + 1
            WHERE id = NEW.company_id;
        END IF;
    ELSIF TG_OP = 'DELETE' AND OLD.status = 'active' THEN
        UPDATE companies 
        SET active_conversations = GREATEST(0, active_conversations - 1)
        WHERE id = OLD.company_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_count_trigger
    AFTER INSERT OR UPDATE OR DELETE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_company_conversation_count();

-- Auto-set closed_at when status changes to closed/won/lost
CREATE OR REPLACE FUNCTION set_conversation_closed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('closed', 'won', 'lost') AND OLD.status NOT IN ('closed', 'won', 'lost') THEN
        NEW.closed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_closed_at_trigger
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION set_conversation_closed_at();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get active conversations for a company
CREATE OR REPLACE FUNCTION get_active_conversations(p_company_id UUID)
RETURNS TABLE (
    conversation_id UUID,
    contact_name TEXT,
    contact_email TEXT,
    status TEXT,
    qualification_tier TEXT,
    touchpoint_count INTEGER,
    last_touchpoint_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        conv.id,
        c.first_name || ' ' || c.last_name,
        c.email,
        conv.status,
        conv.qualification_tier,
        conv.touchpoint_count,
        conv.last_touchpoint_at
    FROM conversations conv
    JOIN contacts c ON conv.contact_id = c.id
    WHERE conv.company_id = p_company_id
    AND conv.status = 'active'
    ORDER BY conv.last_touchpoint_at DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- Get conversations needing follow-up
CREATE OR REPLACE FUNCTION get_conversations_needing_followup()
RETURNS TABLE (
    conversation_id UUID,
    contact_id UUID,
    contact_name TEXT,
    company_name TEXT,
    next_touchpoint_at TIMESTAMPTZ,
    days_overdue INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        conv.id,
        conv.contact_id,
        c.first_name || ' ' || c.last_name,
        comp.name,
        conv.next_touchpoint_at,
        EXTRACT(DAY FROM NOW() - conv.next_touchpoint_at)::INTEGER
    FROM conversations conv
    JOIN contacts c ON conv.contact_id = c.id
    JOIN companies comp ON conv.company_id = comp.id
    WHERE conv.status = 'active'
    AND conv.next_touchpoint_at <= NOW()
    ORDER BY conv.next_touchpoint_at ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE conversations IS 'Tracks conversation state and context for multi-touch ABM campaigns';
COMMENT ON COLUMN conversations.qualification_tier IS 'Lead temperature: scorching, hot, warm, cool, cold';
COMMENT ON COLUMN conversations.context IS 'Conversation context: topics, pain points, objections, interests';
COMMENT ON COLUMN conversations.sequence_step IS 'Current step in automated sequence (0 = not in sequence)';
COMMENT ON FUNCTION get_active_conversations IS 'Get all active conversations for a company';
COMMENT ON FUNCTION get_conversations_needing_followup IS 'Get conversations that need follow-up (overdue touchpoints)';
