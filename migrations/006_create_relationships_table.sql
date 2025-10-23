-- Migration 006: Create Relationships Table for ABM
-- Created: 2025-10-23
-- Purpose: Map relationships between contacts for multi-contact orchestration

-- ============================================================================
-- RELATIONSHIPS TABLE
-- ============================================================================
-- Stores relationships between contacts within and across companies
-- Enables context-aware messaging like "Your colleague Dr. XYZ inquired about..."

CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Contact Pair
    contact_id_1 UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    contact_id_2 UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    
    -- Relationship Details
    relationship_type TEXT NOT NULL,
    -- Types: colleagues, reports_to, manager_of, mentor_mentee, 
    --        collaborators, referral, introduced_by, etc.
    
    strength TEXT DEFAULT 'medium',  -- weak, medium, strong
    
    -- Context & Metadata
    context TEXT,  -- How relationship was discovered
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Structure: {
    --   "discovered_via": "linkedin",
    --   "shared_projects": [...],
    --   "interaction_frequency": "weekly",
    --   "notes": "..."
    -- }
    
    -- Relationship Status
    is_verified BOOLEAN DEFAULT false,
    confidence_score DECIMAL(3,2) DEFAULT 0.5,  -- 0.0 to 1.0
    
    -- Timestamps
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT different_contacts CHECK (contact_id_1 != contact_id_2),
    CONSTRAINT unique_relationship UNIQUE(contact_id_1, contact_id_2)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_relationships_contact1 ON relationships(contact_id_1);
CREATE INDEX IF NOT EXISTS idx_relationships_contact2 ON relationships(contact_id_2);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_strength ON relationships(strength);
CREATE INDEX IF NOT EXISTS idx_relationships_verified ON relationships(is_verified) WHERE is_verified = true;

-- Composite index for bidirectional relationship queries
CREATE INDEX IF NOT EXISTS idx_relationships_both_contacts 
    ON relationships(contact_id_1, contact_id_2);

-- GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_relationships_metadata ON relationships USING GIN(metadata);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_relationships_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER relationships_updated_at_trigger
    BEFORE UPDATE ON relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_relationships_updated_at();

-- Ensure bidirectional uniqueness (prevent duplicate reverse relationships)
CREATE OR REPLACE FUNCTION prevent_duplicate_relationships()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if reverse relationship exists
    IF EXISTS (
        SELECT 1 FROM relationships 
        WHERE contact_id_1 = NEW.contact_id_2 
        AND contact_id_2 = NEW.contact_id_1
    ) THEN
        RAISE EXCEPTION 'Reverse relationship already exists between these contacts';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_duplicate_relationships_trigger
    BEFORE INSERT ON relationships
    FOR EACH ROW
    EXECUTE FUNCTION prevent_duplicate_relationships();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get all relationships for a contact (bidirectional)
CREATE OR REPLACE FUNCTION get_contact_relationships(p_contact_id UUID)
RETURNS TABLE (
    relationship_id UUID,
    related_contact_id UUID,
    relationship_type TEXT,
    strength TEXT,
    is_verified BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id,
        CASE 
            WHEN r.contact_id_1 = p_contact_id THEN r.contact_id_2
            ELSE r.contact_id_1
        END,
        r.relationship_type,
        r.strength,
        r.is_verified
    FROM relationships r
    WHERE r.contact_id_1 = p_contact_id OR r.contact_id_2 = p_contact_id;
END;
$$ LANGUAGE plpgsql;

-- Get colleagues within same company
CREATE OR REPLACE FUNCTION get_colleagues(p_contact_id UUID)
RETURNS TABLE (
    colleague_id UUID,
    colleague_name TEXT,
    colleague_title TEXT,
    relationship_strength TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.first_name || ' ' || c.last_name,
        c.title,
        r.strength
    FROM contacts c
    JOIN relationships r ON (
        (r.contact_id_1 = p_contact_id AND r.contact_id_2 = c.id) OR
        (r.contact_id_2 = p_contact_id AND r.contact_id_1 = c.id)
    )
    WHERE r.relationship_type = 'colleagues'
    AND c.company_id = (SELECT company_id FROM contacts WHERE id = p_contact_id);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE relationships IS 'Maps relationships between contacts for multi-contact ABM orchestration';
COMMENT ON COLUMN relationships.relationship_type IS 'Type: colleagues, reports_to, manager_of, mentor_mentee, collaborators, referral';
COMMENT ON COLUMN relationships.strength IS 'Relationship strength: weak, medium, strong';
COMMENT ON COLUMN relationships.confidence_score IS 'AI confidence in relationship accuracy (0.0-1.0)';
COMMENT ON FUNCTION get_contact_relationships IS 'Get all relationships for a contact (bidirectional)';
COMMENT ON FUNCTION get_colleagues IS 'Get all colleagues of a contact within same company';
