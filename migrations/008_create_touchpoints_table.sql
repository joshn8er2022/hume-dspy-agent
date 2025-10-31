-- Migration 008: Create Touchpoints Table for ABM
-- Created: 2025-10-23
-- Purpose: Track individual communication events within conversations

-- ============================================================================
-- TOUCHPOINTS TABLE
-- ============================================================================
-- Stores individual communication events (emails, calls, SMS, etc.)
-- Tracks delivery, engagement, and response metrics

CREATE TABLE IF NOT EXISTS touchpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relationships
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Communication Details
    channel TEXT NOT NULL,
    -- Channels: email, sms, call, linkedin, mail, whatsapp, meeting
    
    direction TEXT NOT NULL,
    -- Direction: outbound, inbound
    
    -- Content
    subject TEXT,  -- For emails
    content TEXT,  -- Message content
    response TEXT,  -- Response received (for inbound)
    
    -- Engagement Tracking
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    
    -- Outcome
    outcome TEXT,
    -- Outcomes: sent, delivered, opened, clicked, replied, bounced, failed, scheduled
    
    outcome_details TEXT,  -- Additional outcome information
    
    -- Call-specific fields
    call_duration_seconds INTEGER,
    call_recording_url TEXT,
    call_transcript TEXT,
    call_sentiment TEXT,  -- positive, neutral, negative
    
    -- Email-specific fields
    email_thread_id TEXT,  -- For threading
    email_message_id TEXT,  -- External message ID
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "template_id": "...",
    --   "template_name": "...",
    --   "personalization_vars": {...},
    --   "ab_test_variant": "A",
    --   "campaign_id": "...",
    --   "sequence_step": 3,
    --   "sender_id": "...",
    --   "tracking_params": {...},
    --   "attachments": [...]
    -- }
    
    -- Attribution
    created_by_user_id UUID,  -- User who initiated (if manual)
    created_by_automation BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_touchpoints_conversation_id ON touchpoints(conversation_id);
CREATE INDEX IF NOT EXISTS idx_touchpoints_channel ON touchpoints(channel);
CREATE INDEX IF NOT EXISTS idx_touchpoints_direction ON touchpoints(direction);
CREATE INDEX IF NOT EXISTS idx_touchpoints_outcome ON touchpoints(outcome);
CREATE INDEX IF NOT EXISTS idx_touchpoints_sent_at ON touchpoints(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_touchpoints_replied_at ON touchpoints(replied_at DESC) 
    WHERE replied_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_touchpoints_email_thread ON touchpoints(email_thread_id) 
    WHERE email_thread_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_touchpoints_created_at ON touchpoints(created_at DESC);

-- GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_touchpoints_metadata ON touchpoints USING GIN(metadata);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_touchpoints_conversation_channel 
    ON touchpoints(conversation_id, channel);
CREATE INDEX IF NOT EXISTS idx_touchpoints_conversation_created 
    ON touchpoints(conversation_id, created_at DESC);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_touchpoints_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER touchpoints_updated_at_trigger
    BEFORE UPDATE ON touchpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_touchpoints_updated_at();

-- Update conversation touchpoint count and timestamps
CREATE OR REPLACE FUNCTION update_conversation_from_touchpoint()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Increment touchpoint count
        UPDATE conversations 
        SET 
            touchpoint_count = touchpoint_count + 1,
            last_touchpoint_at = NEW.sent_at
        WHERE id = NEW.conversation_id;
        
        -- Update response tracking if this is a reply
        IF NEW.direction = 'inbound' AND NEW.replied_at IS NOT NULL THEN
            UPDATE conversations 
            SET 
                response_count = response_count + 1,
                last_response_at = NEW.replied_at
            WHERE id = NEW.conversation_id;
        END IF;
        
        -- Update contact engagement
        UPDATE contacts c
        SET 
            total_touchpoints = total_touchpoints + 1,
            last_engaged_at = NEW.sent_at
        FROM conversations conv
        WHERE conv.id = NEW.conversation_id
        AND c.id = conv.contact_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER touchpoints_update_conversation_trigger
    AFTER INSERT ON touchpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_from_touchpoint();

-- Auto-set outcome based on engagement events
CREATE OR REPLACE FUNCTION auto_set_touchpoint_outcome()
RETURNS TRIGGER AS $$
BEGIN
    -- Auto-set outcome based on latest engagement event
    IF NEW.replied_at IS NOT NULL AND NEW.outcome IS NULL THEN
        NEW.outcome = 'replied';
    ELSIF NEW.clicked_at IS NOT NULL AND NEW.outcome IS NULL THEN
        NEW.outcome = 'clicked';
    ELSIF NEW.opened_at IS NOT NULL AND NEW.outcome IS NULL THEN
        NEW.outcome = 'opened';
    ELSIF NEW.bounced_at IS NOT NULL AND NEW.outcome IS NULL THEN
        NEW.outcome = 'bounced';
    ELSIF NEW.delivered_at IS NOT NULL AND NEW.outcome IS NULL THEN
        NEW.outcome = 'delivered';
    ELSIF NEW.sent_at IS NOT NULL AND NEW.outcome IS NULL THEN
        NEW.outcome = 'sent';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER touchpoints_auto_outcome_trigger
    BEFORE INSERT OR UPDATE ON touchpoints
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_touchpoint_outcome();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get touchpoint history for a conversation
CREATE OR REPLACE FUNCTION get_touchpoint_history(p_conversation_id UUID)
RETURNS TABLE (
    touchpoint_id UUID,
    channel TEXT,
    direction TEXT,
    subject TEXT,
    outcome TEXT,
    sent_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.channel,
        t.direction,
        t.subject,
        t.outcome,
        t.sent_at,
        t.replied_at
    FROM touchpoints t
    WHERE t.conversation_id = p_conversation_id
    ORDER BY t.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Get engagement metrics for a conversation
CREATE OR REPLACE FUNCTION get_conversation_engagement_metrics(p_conversation_id UUID)
RETURNS TABLE (
    total_touchpoints INTEGER,
    emails_sent INTEGER,
    emails_opened INTEGER,
    emails_clicked INTEGER,
    emails_replied INTEGER,
    open_rate DECIMAL(5,2),
    click_rate DECIMAL(5,2),
    reply_rate DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER,
        COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound')::INTEGER,
        COUNT(*) FILTER (WHERE channel = 'email' AND opened_at IS NOT NULL)::INTEGER,
        COUNT(*) FILTER (WHERE channel = 'email' AND clicked_at IS NOT NULL)::INTEGER,
        COUNT(*) FILTER (WHERE channel = 'email' AND replied_at IS NOT NULL)::INTEGER,
        CASE 
            WHEN COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound') > 0 
            THEN (COUNT(*) FILTER (WHERE channel = 'email' AND opened_at IS NOT NULL)::DECIMAL / 
                  COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound') * 100)
            ELSE 0 
        END,
        CASE 
            WHEN COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound') > 0 
            THEN (COUNT(*) FILTER (WHERE channel = 'email' AND clicked_at IS NOT NULL)::DECIMAL / 
                  COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound') * 100)
            ELSE 0 
        END,
        CASE 
            WHEN COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound') > 0 
            THEN (COUNT(*) FILTER (WHERE channel = 'email' AND replied_at IS NOT NULL)::DECIMAL / 
                  COUNT(*) FILTER (WHERE channel = 'email' AND direction = 'outbound') * 100)
            ELSE 0 
        END
    FROM touchpoints
    WHERE conversation_id = p_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE touchpoints IS 'Individual communication events within conversations';
COMMENT ON COLUMN touchpoints.channel IS 'Communication channel: email, sms, call, linkedin, mail, whatsapp, meeting';
COMMENT ON COLUMN touchpoints.direction IS 'Communication direction: outbound, inbound';
COMMENT ON COLUMN touchpoints.outcome IS 'Final outcome: sent, delivered, opened, clicked, replied, bounced, failed';
COMMENT ON FUNCTION get_touchpoint_history IS 'Get chronological touchpoint history for a conversation';
COMMENT ON FUNCTION get_conversation_engagement_metrics IS 'Calculate engagement metrics (open rate, click rate, reply rate)';
