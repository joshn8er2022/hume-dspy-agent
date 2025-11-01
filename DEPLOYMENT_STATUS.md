# Deployment Status & Debugging Guide

## Current Deployment Issue

**Railway is deploying OLD code!**

- GitHub main branch: `e0a2fcb` (latest)
- Railway deployment: `63dd9b9c` (OLD)
- Missing commits: e0a2fcb, a7e5c5c (critical fixes!)

## Why This Is Happening

Railway auto-deploy might be:
1. Stuck/cached on old commit
2. Not detecting new pushes
3. Rate-limited or throttled

## What's Broken Due to Old Code

### 1. ResearchAgent AsyncIO Error (FIXED in e0a2fcb)
```
UnboundLocalError: cannot access local variable 'asyncio' where it is not associated with a value
```
**Status**: Fix pushed but not deployed

### 2. Delegation JSON Format (FIXED in a7e5c5c)
**Status**: Fix pushed but not deployed

## What's Actually Working

✅ Webhook reception (200 OK)
✅ StrategyAgent initialization
✅ InboundAgent qualification (Score: 37, Tier: COLD)
✅ Delegation reaching agents (correct JSON format in logs)
✅ agent_state table saving (Bug 5 fix working!)

## Phoenix Observability Issue

**Problem**: No traces appearing in Phoenix dashboard

**Root Cause**: `PHOENIX_API_KEY` not set in Railway environment variables

**Evidence from logs**:
```
⚠️ Phoenix tracing disabled - set PHOENIX_API_KEY to enable
```

**Fix**: Add PHOENIX_API_KEY to Railway environment variables

## How to Force Railway to Redeploy Latest Code

### Option 1: Trigger Deploy via Railway CLI
```bash
railway up --detach
```

### Option 2: Make a Trivial Commit
```bash
git commit --allow-empty -m "chore: Force Railway redeploy"
git push
```

### Option 3: Railway Dashboard
1. Go to Railway dashboard
2. Click "Deploy" → "Redeploy"
3. Select latest commit `e0a2fcb`

## Expected Behavior After Correct Deployment

1. ✅ ResearchAgent processes leads without asyncio error
2. ✅ FollowUpAgent receives proper JSON
3. ✅ Full pipeline: Qualify → Research → Follow-up
4. ✅ Slack updates (if leads are saved to DB)

## Critical Commits Pending Deployment

1. **e0a2fcb** - Fix ResearchAgent asyncio error
2. **a7e5c5c** - Fix delegation JSON format
3. **c78a219** - Fix delegation 400 errors
4. **6852eed** - Add Slack error notifications
5. **da054db** - Fix engagement slicing bug

All 5 commits are on GitHub main but NOT deployed to Railway!

## Next Steps

1. Force Railway to deploy latest code (commit e0a2fcb)
2. Add PHOENIX_API_KEY to Railway env vars (optional, for observability)
3. Test webhook with fresh deployment
4. Verify Phoenix traces appear
