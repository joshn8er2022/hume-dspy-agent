-- Migration: Add tier column to leads table
-- Fixes error: column leads.tier does not exist
--
-- Run this in Supabase Dashboard:
-- SQL Editor → New Query → Paste this → Run

-- Add tier column if it doesn't exist
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tier TEXT;

-- Add index for performance (queries by tier are common)
CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);

-- Add index for common queries
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);

-- Set default tier for existing leads without one
UPDATE leads 
SET tier = 'UNQUALIFIED' 
WHERE tier IS NULL;

-- Add check constraint for valid tier values
ALTER TABLE leads 
ADD CONSTRAINT IF NOT EXISTS check_tier_valid 
CHECK (tier IN ('SCORCHING', 'HOT', 'WARM', 'COOL', 'COLD', 'UNQUALIFIED') OR tier IS NULL);

-- Verify the column was added
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'leads' 
  AND column_name = 'tier';

-- Show sample data
SELECT 
    id,
    email,
    first_name,
    tier,
    qualification_score,
    status,
    created_at
FROM leads
ORDER BY created_at DESC
LIMIT 5;
