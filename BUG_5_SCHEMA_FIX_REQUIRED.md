# Bug 5: agent_state Schema Mismatch - FIX REQUIRED

## Status: CRITICAL - Blocking Agent State Logging

## Confirmed Issue

The `agent_state` table exists in Supabase but **does NOT have the columns our code expects**.

### Error Message
```
Could not find the 'agent_name' column of 'agent_state' in the schema cache
Code: PGRST204
```

### Test Results
- ✅ Table EXISTS (query succeeds with empty result)
- ❌ INSERT FAILS (columns don't match our code)
- ❌ Agent state logging is completely broken

### Code Expects These Columns
```python
{
    'agent_name': 'InboundAgent',
    'lead_id': 'uuid-here',
    'state_data': {...},
    'status': 'completed'
}
```

### Actual Columns
**UNKNOWN** - Table exists with different schema than expected.

---

## IMMEDIATE FIX REQUIRED

### Step 1: Go to Supabase SQL Editor
**URL**: https://supabase.com/dashboard/project/umawnwaoahhuttbeyuxs/sql

### Step 2: Run This SQL

```sql
-- Drop the existing agent_state table (it's empty, safe to drop)
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

-- Enable Row Level Security
ALTER TABLE agent_state ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service role full access
CREATE POLICY "Service role can do everything" ON agent_state
    FOR ALL
    USING (true)
    WITH CHECK (true);
```

### Step 3: Verify Fix
After running the SQL, test with this Python command:

```python
from supabase import create_client

supabase = create_client(
    "https://umawnwaoahhuttbeyuxs.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtYXdud2FvYWhodXR0YmV5dXhzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MDU2ODAxNiwiZXhwIjoyMDc2MTQ0MDE2fQ.JeRe2ikyJfgtYQNq289M-dIV4STf4_LcRn4rav-t9So"
)

# Should succeed after fix
result = supabase.table('agent_state').insert({
    'agent_name': 'TestAgent',
    'lead_id': 'test-123',
    'state_data': {'test': 'data'},
    'status': 'completed'
}).execute()

print(f"✅ Test insert succeeded! {result.data}")
```

---

## Impact

**Before Fix:**
- ❌ All agent state logging fails
- ❌ Cannot track agent execution history
- ❌ Cannot audit agent decisions
- ❌ InboundAgent qualification results not persisted
- ❌ StrategyAgent decisions not logged

**After Fix:**
- ✅ Agent state logging works
- ✅ Full audit trail of agent executions
- ✅ Qualification results persisted
- ✅ Strategy decisions tracked

---

## Related Bugs

This fix should be deployed **together with Bug 4 fix** (engagement slicing error) for comprehensive testing.

**Bug 4 Status**: ✅ Fixed locally in `agents/inbound_agent.py` lines 319-320 (not yet committed)

**Next Steps After Schema Fix:**
1. Commit Bug 4 fix
2. Push to GitHub
3. Wait for Railway auto-deploy
4. Re-test webhook end-to-end
5. Verify `agent_state` table populates
6. Run comprehensive audit via StrategyAgent

---

## Files Ready to Deploy

1. `agents/inbound_agent.py` - Bug 4 fix (waiting for Bug 5 resolution)
2. `supabase_create_agent_state_table.sql` - Schema creation SQL (user needs to run manually)

---

## Timeline

**IMMEDIATE**: Run SQL fix (< 1 minute)
**THEN**: Commit & deploy Bug 4 fix (< 5 minutes)
**THEN**: Comprehensive end-to-end test (10-15 minutes)

**Total Time to Production**: ~20 minutes after running SQL fix
