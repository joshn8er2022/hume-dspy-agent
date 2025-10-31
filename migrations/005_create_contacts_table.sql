-- Migration 005: Create Contacts Table for ABM
-- Created: 2025-10-23
-- Purpose: Store individual contacts within companies for multi-contact orchestration

-- ============================================================================
-- CONTACTS TABLE
-- ============================================================================
-- Stores individual contacts within companies
-- Enables multi-contact ABM campaigns and relationship mapping

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Company Relationship
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Basic Info
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    
    -- Professional Info
    title TEXT,
    role TEXT,  -- doctor, admin, executive, manager, staff, etc.
    department TEXT,
    seniority_level TEXT,  -- c-level, vp, director, manager, individual_contributor
    
    -- Social & Web Presence
    linkedin_url TEXT,
    twitter_url TEXT,
    personal_website TEXT,
    
    -- Interests & Preferences
    interests JSONB DEFAULT '[]'::jsonb,
    -- Structure: ["topic1", "topic2", ...]
    
    communication_preferences JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "preferred_channel": "email",
    --   "best_time": "morning",
    --   "timezone": "America/New_York",
    --   "do_not_contact": false
    -- }
    
    -- Research & Enrichment Data
    research_data JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "bio": "...",
    --   "background": "...",
    --   "education": [...],
    --   "career_history": [...],
    --   "publications": [...],
    --   "speaking_engagements": [...],
    --   "social_activity": {...}
    -- }
    
    -- Engagement Metadata
    engagement_score INTEGER DEFAULT 0,  -- 0-100
    last_engaged_at TIMESTAMPTZ,
    total_touchpoints INTEGER DEFAULT 0,
    
    -- Contact Status
    status TEXT DEFAULT 'active',  -- active, unsubscribed, bounced, invalid
    is_primary_contact BOOLEAN DEFAULT false,
    is_decision_maker BOOLEAN DEFAULT false,
    is_champion BOOLEAN DEFAULT false,
    
    -- Timestamps
    last_researched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_role ON contacts(role);
CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
CREATE INDEX IF NOT EXISTS idx_contacts_is_primary ON contacts(is_primary_contact) WHERE is_primary_contact = true;
CREATE INDEX IF NOT EXISTS idx_contacts_is_decision_maker ON contacts(is_decision_maker) WHERE is_decision_maker = true;
CREATE INDEX IF NOT EXISTS idx_contacts_engagement_score ON contacts(engagement_score DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at DESC);

-- GIN indexes for JSONB queries
CREATE INDEX IF NOT EXISTS idx_contacts_interests ON contacts USING GIN(interests);
CREATE INDEX IF NOT EXISTS idx_contacts_research_data ON contacts USING GIN(research_data);

-- Composite index for company + role queries
CREATE INDEX IF NOT EXISTS idx_contacts_company_role ON contacts(company_id, role);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_contacts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER contacts_updated_at_trigger
    BEFORE UPDATE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_contacts_updated_at();

-- Update company contact count
CREATE OR REPLACE FUNCTION update_company_contact_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE companies 
        SET total_contacts = total_contacts + 1
        WHERE id = NEW.company_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE companies 
        SET total_contacts = GREATEST(0, total_contacts - 1)
        WHERE id = OLD.company_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER contacts_count_trigger
    AFTER INSERT OR DELETE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_company_contact_count();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE contacts IS 'Individual contacts within companies for ABM campaigns';
COMMENT ON COLUMN contacts.role IS 'Professional role: doctor, admin, executive, manager, staff';
COMMENT ON COLUMN contacts.interests IS 'Array of topics/interests for personalization';
COMMENT ON COLUMN contacts.research_data IS 'Cached enrichment data from Research Agent';
COMMENT ON COLUMN contacts.engagement_score IS 'Engagement level 0-100 based on interactions';
