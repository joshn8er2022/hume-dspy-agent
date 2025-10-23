-- Migration 009: Create Performance Indexes for ABM
-- Created: 2025-10-23
-- Purpose: Add additional performance indexes for common ABM query patterns

-- ============================================================================
-- CROSS-TABLE QUERY OPTIMIZATION
-- ============================================================================

-- Company + Contacts queries
CREATE INDEX IF NOT EXISTS idx_contacts_company_status 
    ON contacts(company_id, status) 
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_contacts_company_primary 
    ON contacts(company_id, is_primary_contact) 
    WHERE is_primary_contact = true;

CREATE INDEX IF NOT EXISTS idx_contacts_company_decision_maker 
    ON contacts(company_id, is_decision_maker) 
    WHERE is_decision_maker = true;

-- Conversation + Touchpoint queries
CREATE INDEX IF NOT EXISTS idx_touchpoints_conversation_outcome 
    ON touchpoints(conversation_id, outcome);

CREATE INDEX IF NOT EXISTS idx_touchpoints_conversation_replied 
    ON touchpoints(conversation_id, replied_at DESC) 
    WHERE replied_at IS NOT NULL;

-- Company + Conversation queries
CREATE INDEX IF NOT EXISTS idx_conversations_company_tier 
    ON conversations(company_id, qualification_tier) 
    WHERE status = 'active';

-- ============================================================================
-- FULL-TEXT SEARCH INDEXES
-- ============================================================================

-- Full-text search on company names and descriptions
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm 
    ON companies USING gin(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_companies_description_trgm 
    ON companies USING gin(description gin_trgm_ops);

-- Full-text search on contact names
CREATE INDEX IF NOT EXISTS idx_contacts_name_trgm 
    ON contacts USING gin((first_name || ' ' || last_name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_contacts_title_trgm 
    ON contacts USING gin(title gin_trgm_ops);

-- Full-text search on touchpoint content
CREATE INDEX IF NOT EXISTS idx_touchpoints_content_trgm 
    ON touchpoints USING gin(content gin_trgm_ops);

-- ============================================================================
-- TIME-BASED QUERY OPTIMIZATION
-- ============================================================================

-- Recent activity queries
CREATE INDEX IF NOT EXISTS idx_companies_recent_research 
    ON companies(last_researched_at DESC NULLS LAST) 
    WHERE last_researched_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_recent_engagement 
    ON contacts(last_engaged_at DESC NULLS LAST) 
    WHERE last_engaged_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_recent_touchpoint 
    ON conversations(last_touchpoint_at DESC NULLS LAST) 
    WHERE status = 'active';

-- Scheduled follow-ups
CREATE INDEX IF NOT EXISTS idx_conversations_upcoming_touchpoints 
    ON conversations(next_touchpoint_at ASC) 
    WHERE status = 'active' AND next_touchpoint_at IS NOT NULL;

-- ============================================================================
-- ANALYTICS & REPORTING INDEXES
-- ============================================================================

-- Engagement analytics
CREATE INDEX IF NOT EXISTS idx_touchpoints_channel_outcome 
    ON touchpoints(channel, outcome, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_touchpoints_sent_date 
    ON touchpoints(DATE(sent_at)) 
    WHERE sent_at IS NOT NULL;

-- Conversation analytics
CREATE INDEX IF NOT EXISTS idx_conversations_status_tier 
    ON conversations(status, qualification_tier);

CREATE INDEX IF NOT EXISTS idx_conversations_outcome_date 
    ON conversations(outcome, outcome_date DESC) 
    WHERE outcome IS NOT NULL;

-- Company analytics
CREATE INDEX IF NOT EXISTS idx_companies_tier_status 
    ON companies(account_tier, account_status);

-- ============================================================================
-- RELATIONSHIP GRAPH QUERIES
-- ============================================================================

-- Bidirectional relationship lookups
CREATE INDEX IF NOT EXISTS idx_relationships_type_strength 
    ON relationships(relationship_type, strength);

-- Company network analysis
CREATE INDEX IF NOT EXISTS idx_relationships_company_network 
    ON relationships(contact_id_1, contact_id_2) 
    INCLUDE (relationship_type, strength);

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC USE CASES
-- ============================================================================

-- Hot leads requiring immediate attention
CREATE INDEX IF NOT EXISTS idx_conversations_hot_leads 
    ON conversations(qualification_tier, next_touchpoint_at) 
    WHERE status = 'active' 
    AND qualification_tier IN ('scorching', 'hot');

-- Stale conversations needing re-engagement
CREATE INDEX IF NOT EXISTS idx_conversations_stale 
    ON conversations(last_touchpoint_at) 
    WHERE status = 'active' 
    AND last_touchpoint_at < NOW() - INTERVAL '30 days';

-- Bounced/invalid contacts
CREATE INDEX IF NOT EXISTS idx_contacts_invalid 
    ON contacts(status, updated_at DESC) 
    WHERE status IN ('bounced', 'invalid', 'unsubscribed');

-- High-value opportunities
CREATE INDEX IF NOT EXISTS idx_conversations_high_value 
    ON conversations(estimated_value DESC, qualification_tier) 
    WHERE status = 'active' 
    AND estimated_value > 0;

-- ============================================================================
-- MATERIALIZED VIEW FOR ACCOUNT OVERVIEW
-- ============================================================================

-- Create materialized view for fast account overview queries
CREATE MATERIALIZED VIEW IF NOT EXISTS account_overview AS
SELECT 
    comp.id AS company_id,
    comp.name AS company_name,
    comp.domain,
    comp.industry,
    comp.account_tier,
    comp.account_status,
    
    -- Contact counts
    COUNT(DISTINCT c.id) AS total_contacts,
    COUNT(DISTINCT c.id) FILTER (WHERE c.is_primary_contact) AS primary_contacts,
    COUNT(DISTINCT c.id) FILTER (WHERE c.is_decision_maker) AS decision_makers,
    
    -- Conversation metrics
    COUNT(DISTINCT conv.id) AS total_conversations,
    COUNT(DISTINCT conv.id) FILTER (WHERE conv.status = 'active') AS active_conversations,
    COUNT(DISTINCT conv.id) FILTER (WHERE conv.status = 'won') AS won_conversations,
    
    -- Engagement metrics
    COUNT(DISTINCT t.id) AS total_touchpoints,
    COUNT(DISTINCT t.id) FILTER (WHERE t.replied_at IS NOT NULL) AS total_replies,
    MAX(t.sent_at) AS last_touchpoint_at,
    MAX(t.replied_at) AS last_reply_at,
    
    -- Relationship metrics
    COUNT(DISTINCT r.id) AS total_relationships,
    
    -- Timestamps
    comp.created_at,
    comp.updated_at
    
FROM companies comp
LEFT JOIN contacts c ON c.company_id = comp.id
LEFT JOIN conversations conv ON conv.company_id = comp.id
LEFT JOIN touchpoints t ON t.conversation_id = conv.id
LEFT JOIN relationships r ON r.contact_id_1 = c.id OR r.contact_id_2 = c.id
GROUP BY comp.id;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_account_overview_company_id 
    ON account_overview(company_id);

CREATE INDEX IF NOT EXISTS idx_account_overview_tier_status 
    ON account_overview(account_tier, account_status);

CREATE INDEX IF NOT EXISTS idx_account_overview_active_conversations 
    ON account_overview(active_conversations DESC) 
    WHERE active_conversations > 0;

-- ============================================================================
-- REFRESH FUNCTION FOR MATERIALIZED VIEW
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_account_overview()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY account_overview;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STATISTICS UPDATES
-- ============================================================================

-- Ensure PostgreSQL has up-to-date statistics for query planning
ANALYZE companies;
ANALYZE contacts;
ANALYZE relationships;
ANALYZE conversations;
ANALYZE touchpoints;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON MATERIALIZED VIEW account_overview IS 'Aggregated account metrics for fast dashboard queries';
COMMENT ON FUNCTION refresh_account_overview IS 'Refresh account overview materialized view (call periodically)';

-- ============================================================================
-- PERFORMANCE NOTES
-- ============================================================================

-- To refresh the materialized view periodically, set up a cron job or use pg_cron:
-- SELECT cron.schedule('refresh-account-overview', '*/15 * * * *', 'SELECT refresh_account_overview();');

-- For optimal performance:
-- 1. Run ANALYZE after bulk data loads
-- 2. Refresh account_overview materialized view every 15-30 minutes
-- 3. Monitor slow queries and add indexes as needed
-- 4. Consider partitioning touchpoints table by date if volume is very high
