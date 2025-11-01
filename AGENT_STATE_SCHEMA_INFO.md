# agent_state Table Schema Investigation

## Problem
The `agent_state` table exists in Supabase but has different columns than our code expects.

Our code tries to insert:
```python
{
    'agent_name': 'InboundAgent',     # Column doesn't exist!
    'lead_id': 'uuid-here',           # Column doesn't exist!
    'state_data': {...},              # Column doesn't exist!
    'status': 'completed'             # Column doesn't exist!
}
```

Error received:
```
Could not find the 'agent_name' column of 'agent_state' in the schema cache
```

## How to Check Actual Schema

### Option 1: Supabase Dashboard (EASIEST)
1. Go to: https://supabase.com/dashboard/project/umawnwaoahhuttbeyuxs/editor
2. Click **"Table Editor"** in left sidebar
3. Find and click **"agent_state"** table
4. View the column list

### Option 2: SQL Editor
1. Go to: https://supabase.com/dashboard/project/umawnwaoahhuttbeyuxs/sql
2. Run this query:
```sql
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'agent_state'
ORDER BY ordinal_position;
```

## Expected Schema (What Our Code Needs)

```sql
CREATE TABLE agent_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,              -- ← Our code needs this
    lead_id TEXT NOT NULL,                 -- ← Our code needs this
    state_data JSONB DEFAULT '{}'::jsonb,  -- ← Our code needs this
    status TEXT DEFAULT 'pending',         -- ← Our code needs this
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Solutions

### Solution 1: Drop and Recreate (RECOMMENDED - table is empty)
Since the table is empty, we can safely drop and recreate:

```sql
-- Drop the existing table
DROP TABLE IF EXISTS agent_state CASCADE;

-- Create with correct schema
CREATE TABLE agent_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    state_data JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_agent_state_lead_id ON agent_state(lead_id);
CREATE INDEX idx_agent_state_agent_name ON agent_state(agent_name);
CREATE INDEX idx_agent_state_created_at ON agent_state(created_at DESC);
```

### Solution 2: Alter Table (If you want to keep existing structure)
If the table has data or you want to keep the existing columns:

```sql
-- Add missing columns
ALTER TABLE agent_state ADD COLUMN IF NOT EXISTS agent_name TEXT;
ALTER TABLE agent_state ADD COLUMN IF NOT EXISTS lead_id TEXT;
ALTER TABLE agent_state ADD COLUMN IF NOT EXISTS state_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE agent_state ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
```

## Action Required

**Please:**
1. Check the actual schema using one of the methods above
2. Share the current column list here
3. Then run Solution 1 (drop & recreate) since table is empty

This will fix the schema mismatch and allow agent_state logging to work.
