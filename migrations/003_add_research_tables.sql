-- Migration 003: Add Research Intelligence Tables
-- Created: 2025-10-17
-- Purpose: Store enriched research data from Research Agent

-- ============================================================================
-- PERSON PROFILES (Enriched Individual Data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS person_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    
    -- Basic Info
    name TEXT NOT NULL,
    email TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    bio TEXT,
    
    -- Professional Links
    linkedin_url TEXT,
    twitter_handle TEXT,
    facebook_handle TEXT,
    
    -- Experience & Education (JSONB for flexibility)
    experience JSONB DEFAULT '[]'::jsonb,
    education JSONB DEFAULT '[]'::jsonb,
    
    -- Activity & Presence
    recent_activity JSONB DEFAULT '[]'::jsonb,
    social_presence JSONB DEFAULT '{}'::jsonb,
    
    -- Metadata
    research_source TEXT, -- 'clearbit', 'apollo', 'manual', etc.
    research_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    UNIQUE(lead_id)
);

CREATE INDEX idx_person_profiles_email ON person_profiles(email);
CREATE INDEX idx_person_profiles_company ON person_profiles(company);
CREATE INDEX idx_person_profiles_research_timestamp ON person_profiles(research_timestamp);

-- ============================================================================
-- COMPANY PROFILES (Enriched Company Data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Info
    name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    description TEXT,
    
    -- Firmographics
    employee_count INTEGER,
    founded_year INTEGER,
    headquarters TEXT,
    
    -- Funding Info
    funding_stage TEXT, -- 'seed', 'series_a', 'series_b', 'public', etc.
    total_funding_usd BIGINT,
    last_funding_date DATE,
    
    -- Technology
    tech_stack JSONB DEFAULT '[]'::jsonb,
    
    -- Social & Web Presence
    website_url TEXT,
    linkedin_url TEXT,
    twitter_handle TEXT,
    facebook_url TEXT,
    social_links JSONB DEFAULT '{}'::jsonb,
    
    -- Intelligence
    recent_news JSONB DEFAULT '[]'::jsonb,
    competitors JSONB DEFAULT '[]'::jsonb,
    key_decision_makers JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    research_source TEXT,
    research_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    UNIQUE(domain)
);

CREATE INDEX idx_company_profiles_name ON company_profiles(name);
CREATE INDEX idx_company_profiles_domain ON company_profiles(domain);
CREATE INDEX idx_company_profiles_industry ON company_profiles(industry);
CREATE INDEX idx_company_profiles_employee_count ON company_profiles(employee_count);

-- ============================================================================
-- ACCOUNT CONTACTS (Multi-Contact Strategy)
-- ============================================================================

CREATE TABLE IF NOT EXISTS account_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Company Association
    company_domain TEXT NOT NULL,
    company_name TEXT NOT NULL,
    
    -- Contact Info
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    title TEXT,
    department TEXT,
    seniority TEXT, -- 'entry', 'mid', 'senior', 'executive', 'c_level'
    
    -- Professional Links
    linkedin_url TEXT,
    
    -- Engagement Tracking
    engagement_status TEXT DEFAULT 'not_contacted', -- 'not_contacted', 'contacted', 'engaged', 'qualified', 'customer'
    first_contact_date TIMESTAMP WITH TIME ZONE,
    last_contact_date TIMESTAMP WITH TIME ZONE,
    contact_attempts INTEGER DEFAULT 0,
    
    -- Relationship to Primary Lead
    primary_lead_id UUID REFERENCES leads(id),
    relationship_type TEXT, -- 'coworker', 'manager', 'subordinate', 'decision_maker'
    
    -- Metadata
    source TEXT, -- 'apollo', 'linkedin', 'manual', 'referral'
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_account_contacts_company_domain ON account_contacts(company_domain);
CREATE INDEX idx_account_contacts_email ON account_contacts(email);
CREATE INDEX idx_account_contacts_engagement_status ON account_contacts(engagement_status);
CREATE INDEX idx_account_contacts_primary_lead ON account_contacts(primary_lead_id);

-- ============================================================================
-- RESEARCH TASKS (Async Research Queue)
-- ============================================================================

CREATE TABLE IF NOT EXISTS research_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT UNIQUE NOT NULL,
    
    -- Task Details
    task_type TEXT NOT NULL, -- 'person', 'company', 'contacts', 'deep_research'
    lead_id UUID REFERENCES leads(id),
    parameters JSONB DEFAULT '{}'::jsonb,
    
    -- Status
    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
    progress INTEGER DEFAULT 0, -- 0-100
    
    -- Results
    result_data JSONB,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_research_tasks_status ON research_tasks(status);
CREATE INDEX idx_research_tasks_task_type ON research_tasks(task_type);
CREATE INDEX idx_research_tasks_lead_id ON research_tasks(lead_id);
CREATE INDEX idx_research_tasks_created_at ON research_tasks(created_at);

-- ============================================================================
-- LEAD ENRICHMENT SCORES (Track Research Quality)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lead_enrichment_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE UNIQUE,
    
    -- Research Completeness
    has_person_profile BOOLEAN DEFAULT FALSE,
    has_company_profile BOOLEAN DEFAULT FALSE,
    additional_contacts_count INTEGER DEFAULT 0,
    
    -- Quality Scores (0-100)
    person_data_score INTEGER DEFAULT 0,
    company_data_score INTEGER DEFAULT 0,
    overall_research_score INTEGER DEFAULT 0,
    
    -- Intelligence Flags
    has_linkedin_profile BOOLEAN DEFAULT FALSE,
    has_company_tech_stack BOOLEAN DEFAULT FALSE,
    has_recent_news BOOLEAN DEFAULT FALSE,
    has_decision_maker_map BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    last_researched_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_lead_enrichment_scores_overall_score ON lead_enrichment_scores(overall_research_score);
CREATE INDEX idx_lead_enrichment_scores_last_researched ON lead_enrichment_scores(last_researched_at);

-- ============================================================================
-- UPDATE TRIGGERS
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_person_profiles_updated_at BEFORE UPDATE ON person_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_company_profiles_updated_at BEFORE UPDATE ON company_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_account_contacts_updated_at BEFORE UPDATE ON account_contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_research_tasks_updated_at BEFORE UPDATE ON research_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lead_enrichment_scores_updated_at BEFORE UPDATE ON lead_enrichment_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Enriched Leads (Join leads with research data)
CREATE OR REPLACE VIEW enriched_leads AS
SELECT 
    l.*,
    pp.title AS person_title,
    pp.linkedin_url,
    cp.industry AS company_industry,
    cp.employee_count AS company_size,
    cp.tech_stack AS company_tech_stack,
    les.overall_research_score,
    les.additional_contacts_count,
    ac_count.contact_count AS total_contacts_at_company
FROM leads l
LEFT JOIN person_profiles pp ON l.id = pp.lead_id
LEFT JOIN company_profiles cp ON l.company = cp.name OR l.email LIKE '%@' || cp.domain
LEFT JOIN lead_enrichment_scores les ON l.id = les.lead_id
LEFT JOIN (
    SELECT company_domain, COUNT(*) as contact_count
    FROM account_contacts
    GROUP BY company_domain
) ac_count ON cp.domain = ac_count.company_domain;

-- View: Research Coverage (Track which leads need research)
CREATE OR REPLACE VIEW research_coverage AS
SELECT 
    l.id AS lead_id,
    l.email,
    l.company,
    l.qualification_tier,
    CASE 
        WHEN pp.id IS NOT NULL THEN TRUE ELSE FALSE 
    END AS has_person_research,
    CASE 
        WHEN cp.id IS NOT NULL THEN TRUE ELSE FALSE 
    END AS has_company_research,
    COALESCE(les.overall_research_score, 0) AS research_score,
    COALESCE(les.additional_contacts_count, 0) AS additional_contacts,
    CASE 
        WHEN pp.id IS NULL AND l.qualification_tier IN ('HOT', 'SCORCHING') THEN TRUE
        ELSE FALSE
    END AS needs_research
FROM leads l
LEFT JOIN person_profiles pp ON l.id = pp.lead_id
LEFT JOIN company_profiles cp ON l.company = cp.name
LEFT JOIN lead_enrichment_scores les ON l.id = les.lead_id;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE person_profiles IS 'Enriched individual profiles from research (Clearbit, LinkedIn, etc)';
COMMENT ON TABLE company_profiles IS 'Enriched company profiles from research (Clearbit, BuiltWith, etc)';
COMMENT ON TABLE account_contacts IS 'Additional contacts at accounts for multi-touch outreach';
COMMENT ON TABLE research_tasks IS 'Async research task queue and status tracking';
COMMENT ON TABLE lead_enrichment_scores IS 'Track research completeness and quality for each lead';

-- ============================================================================
-- GRANTS (Adjust based on your role setup)
-- ============================================================================

-- Grant appropriate permissions (example for service role)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
