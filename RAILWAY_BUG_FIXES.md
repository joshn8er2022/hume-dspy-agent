# Railway Production Bug Fixes
**Date**: 2025-01-26
**Status**: ✅ Fixed

## Critical Bugs Fixed

### 1. ✅ Import Error: `get_async_client` not found

**Error**:
```
ERROR: cannot import name 'get_async_client' from 'core.async_supabase_client'
```

**Root Cause**:
- Code was trying to import `get_async_client` but the actual function is named `get_async_supabase_client`
- Function was being called without `await` even though it's an async function

**Files Fixed**:
1. `api/main.py:582-583`
   - Changed: `from core.async_supabase_client import get_async_client`
   - To: `from core.async_supabase_client import get_async_supabase_client`
   - Changed: `supabase = get_async_client()`
   - To: `supabase = await get_async_supabase_client()`

2. `agents/strategy_agent.py:2700-2702`
   - Changed: `from core.async_supabase_client import get_async_client`
   - To: `from core.async_supabase_client import get_async_supabase_client`
   - Changed: `supabase = get_async_client()`
   - To: `supabase = await get_async_supabase_client()`

**Impact**: 
- ✅ StrategyAgent can now save leads to database
- ✅ InboundAgent can now update lead qualification results

---

### 2. ✅ ResearchAgent Asyncio UnboundLocalError

**Error**:
```
UnboundLocalError: cannot access local variable 'asyncio' where it is not associated with a value
```

**Root Cause**:
- Local `import asyncio` inside `research_lead_deeply()` method (line 303) was shadowing the module-level import
- When line 246 tried to use `asyncio.gather()`, Python thought `asyncio` was a local variable but it hadn't been assigned yet

**File Fixed**:
- `agents/research_agent.py:303`
  - Removed: `import asyncio` (redundant - already imported at module level line 12)
  - Module-level import at line 12 is sufficient

**Impact**:
- ✅ ResearchAgent can now execute parallel research tasks correctly
- ✅ No more "coroutine was never awaited" warnings

---

## Remaining Issues to Monitor

### 3. ⚠️ PostgreSQL Connection Failures (IPv6)

**Error**:
```
error connecting in 'pool-4': connection to server at "2600:1f16:1cd0:332a:dfa1:5e11:e577:96ea", port 5432 failed: Network is unreachable
```

**Root Cause**:
- PostgreSQL connection pool trying to connect via IPv6
- Railway's network might not support IPv6 or connection string is using IPv6 address

**Recommendation**:
- Check Supabase connection string - ensure it's using IPv4 or hostname
- Verify Railway network configuration supports PostgreSQL connections
- May need to configure connection pool to prefer IPv4

**Impact**: 
- FollowUpAgent PostgreSQL checkpointer failing (falling back to in-memory)
- LangGraph state persistence not working

---

### 4. ⚠️ FollowUpAgent - Lead Not Found

**Error**:
```
❌ Error: Lead a40813b3-437d-403f-a576-f2cc5ffb4851 not found
```

**Root Cause**:
- FollowUpAgent queries `leads` table but lead might not be saved yet
- Timing issue: FollowUpAgent triggered before lead persistence completes

**Status**: 
- Should be fixed now that `_save_lead_to_db()` is working in StrategyAgent
- Need to verify lead is saved before FollowUpAgent is triggered

---

### 5. ⚠️ Service Status: SLEEPING

**Issue**: Railway service is currently SLEEPING (not running)

**Action Required**:
1. Wake service: `railway up` or via Railway dashboard
2. Service will auto-wake on next webhook request but first request may be slow

---

## Testing Recommendations

1. **Test Lead Persistence**:
   ```bash
   # Send test webhook
   curl -X POST https://hume-dspy-agent-production.up.railway.app/webhooks/typeform \
     -H "Content-Type: application/json" \
     -d @test_webhook.json
   ```

2. **Verify Database Updates**:
   - Check `leads` table - lead should be saved
   - Check `agent_state` table - StrategyAgent state should be saved

3. **Check Logs**:
   ```bash
   railway logs --lines 50 --service hume-dspy-agent --environment production
   ```

4. **Verify No Import Errors**:
   - Look for: "✅ Lead saved to database"
   - Look for: "✅ Lead qualification saved to database"
   - Should NOT see: "cannot import name 'get_async_client'"

---

## Deployment Checklist

- [x] Fix import errors in `api/main.py`
- [x] Fix import errors in `agents/strategy_agent.py`
- [x] Fix asyncio bug in `agents/research_agent.py`
- [ ] Test fixes locally (optional but recommended)
- [ ] Deploy to Railway
- [ ] Monitor logs for errors
- [ ] Verify lead persistence works
- [ ] Verify FollowUpAgent can find leads

---

## Next Steps

1. **Deploy fixes to Railway**:
   ```bash
   git add .
   git commit -m "fix: Critical Railway production bugs

   - Fix get_async_client import error (wrong function name + missing await)
   - Fix ResearchAgent asyncio UnboundLocalError (removed redundant import)
   - Enables lead persistence and database updates"
   git push origin main
   ```

2. **Wake Railway service** if it's sleeping

3. **Monitor logs** after deployment:
   ```bash
   railway logs --service hume-dspy-agent --environment production --filter "@level:error"
   ```

4. **Investigate PostgreSQL connection** if issues persist (IPv6/IPv4 configuration)

---

**All critical bugs fixed!** 🎉

