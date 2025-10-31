-- Migration 004: Create Companies Table for ABM
-- Created: 2025-10-23
-- Purpose: Store company/account data for Account-Based Marketing

-- ============================================================================
-- COMPANIES TABLE
-- ============================================================================
-- Stores company/account information for ABM campaigns
-- Links to contacts, conversations, and research data

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core Company Info
    name TEXT NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    industry TEXT,
    size TEXT,  -- small, medium, large, enterprise
    description TEXT,
    
    -- Location
    headquarters_location TEXT,
    country TEXT,
    
    -- Research & Enrichment Data
    research_data JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "company_overview": "...",
    --   "key_initiatives": [...],
    --   "pain_points": [...],
    --   "tech_stack": [...],
    --   "recent_news": [...],
    --   "funding_info": {...},
    --   "employee_count": 123,
    --   "growth_signals": [...]
    -- }
    
    -- ABM Metadata
    account_tier TEXT,  -- strategic, tier1, tier2, tier3
    account_status TEXT DEFAULT 'prospecting',  -- prospecting, engaged, customer, churned
    total_contacts INTEGER DEFAULT 0,
    active_conversations INTEGER DEFAULT 0,
    
    -- Timestamps
    last_researched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain);
CREATE INDEX IF NOT EXISTS idx_companies_industry ON companies(industry);
CREATE INDEX IF NOT EXISTS idx_companies_account_tier ON companies(account_tier);
CREATE INDEX IF NOT EXISTS idx_companies_account_status ON companies(account_status);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies(created_at DESC);

-- GIN index for JSONB research data queries
CREATE INDEX IF NOT EXISTS idx_companies_research_data ON companies USING GIN(research_data);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_companies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_updated_at_trigger
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_companies_updated_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE companies IS 'Stores company/account data for ABM campaigns';
COMMENT ON COLUMN companies.research_data IS 'Cached research results from Research Agent';
COMMENT ON COLUMN companies.account_tier IS 'Strategic importance: strategic, tier1, tier2, tier3';
COMMENT ON COLUMN companies.account_status IS 'Current relationship status: prospecting, engaged, customer, churned';
