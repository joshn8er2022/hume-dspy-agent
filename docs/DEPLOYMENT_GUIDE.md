# Phase 4 Deployment Guide

## Pre-Deployment Checklist

### 1. Code Review

- [x] InboundAgent integration complete
- [x] FollowUpAgent integration complete
- [x] QualificationResult model updated
- [x] Tests created and passing
- [x] Documentation complete

### 2. Environment Variables

Verify all required environment variables are set in Railway:

```bash
# Core
SUPABASE_URL=<your_url>
SUPABASE_KEY=<your_key>
OPENAI_API_KEY=<your_key>

# Research (Optional but recommended)
APOLLO_API_KEY=<your_key>
CLEARBIT_API_KEY=<your_key>

# Communication
GMASS_API_KEY=<your_key>
TWILIO_ACCOUNT_SID=<your_sid>
TWILIO_AUTH_TOKEN=<your_token>
TWILIO_PHONE_NUMBER=<your_number>

# Slack
SLACK_BOT_TOKEN=<your_token>
SLACK_CHANNEL_ID=<your_channel>

# Phoenix (Optional)
PHOENIX_API_KEY=<your_key>
PHOENIX_PROJECT_ID=<your_project>
```

### 3. Database Schema

Verify Supabase tables exist:
- `companies`
- `contacts`
- `relationships`
- `campaigns`
- `touchpoints`
- `accounts`

Run migrations if needed:
```bash
# Check if tables exist
psql $DATABASE_URL -c "\dt"

# Create tables if missing (handled by AccountOrchestrator on first run)
```

### 4. Backup Current Production

```bash
# Backup current agents
cp agents/inbound_agent.py agents/inbound_agent.py.backup_pre_phase4
cp agents/follow_up_agent.py agents/follow_up_agent.py.backup_pre_phase4
cp models/qualification.py models/qualification.py.backup_pre_phase4
```

## Deployment Steps

### Step 1: Local Testing

```bash
# Run all tests
pytest tests/test_e2e_abm.py -v

# Run existing tests to ensure no breaking changes
pytest tests/test_abm_integration.py -v
pytest tests/test_account_orchestrator.py -v

# Verify imports
python -c "from agents.inbound_agent import InboundAgent; print('✅ InboundAgent OK')"
python -c "from agents.follow_up_agent import FollowUpAgent; print('✅ FollowUpAgent OK')"
python -c "from agents.account_orchestrator import AccountOrchestrator; print('✅ AccountOrchestrator OK')"
```

### Step 2: Commit Changes

```bash
# Stage changes
git add agents/inbound_agent.py
git add agents/follow_up_agent.py
git add agents/account_orchestrator.py
git add models/qualification.py
git add core/company_graph.py
git add core/abm_data.py
git add tests/test_e2e_abm.py
git add docs/INTEGRATION_GUIDE.md
git add docs/DEPLOYMENT_GUIDE.md

# Commit
git commit -m "Phase 4: ABM Integration - InboundAgent + FollowUpAgent + AccountOrchestrator

- Integrated AccountOrchestrator with InboundAgent for automatic ABM campaign initiation
- Extended FollowUpAgent to support multi-contact campaigns
- Added campaign_id field to QualificationResult model
- Created comprehensive end-to-end integration tests
- Added documentation for integration and deployment

Features:
- Automatic ABM campaigns for HOT/SCORCHING/WARM leads
- Multi-contact outreach (primary + colleagues)
- Graceful degradation on failures
- Full integration with existing qualification flow
"

# Push to GitHub (triggers Railway auto-deploy)
git push origin main
```

### Step 3: Monitor Railway Deployment

1. **Watch Build Logs**:
   - Go to Railway dashboard
   - Select your service
   - Click "Deployments" tab
   - Watch build progress

2. **Check for Errors**:
   ```
   Expected output:
   ✅ Building...
   ✅ Installing dependencies...
   ✅ Starting application...
   ✅ Health check passed
   ```

3. **Verify Service Start**:
   - Check application logs
   - Look for startup messages
   - Verify no import errors

### Step 4: Smoke Testing

#### Test 1: Submit Test Lead

```bash
# Submit via Typeform or API
curl -X POST https://your-app.railway.app/webhook/typeform \
  -H "Content-Type: application/json" \
  -d '{
    "form_response": {
      "answers": [
        {"field": {"ref": "first_name"}, "text": "Test"},
        {"field": {"ref": "last_name"}, "text": "User"},
        {"field": {"ref": "email"}, "email": "test@example.com"},
        {"field": {"ref": "company"}, "text": "Test Healthcare"},
        {"field": {"ref": "business_size"}, "choice": {"label": "50-200 employees"}},
        {"field": {"ref": "patient_volume"}, "choice": {"label": "1000+ patients"}}
      ]
    }
  }'
```

#### Test 2: Check Logs

```bash
# Look for ABM campaign initiation
railway logs | grep "ABM Campaign initiated"

# Expected output:
# 🎯 ABM Campaign initiated: campaign-abc123 for test@example.com (tier: hot)
```

#### Test 3: Verify Database

```bash
# Check campaign created
psql $DATABASE_URL -c "SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 1;"

# Check account created
psql $DATABASE_URL -c "SELECT * FROM accounts WHERE company_name = 'Test Healthcare';"
```

### Step 5: Monitor Production

#### Key Metrics to Watch

1. **Campaign Initiation Rate**
   - Expected: 60-80% of qualified leads (HOT/SCORCHING/WARM)
   - Alert if: < 50%

2. **Error Rate**
   - Expected: < 5% (graceful degradation)
   - Alert if: > 10%

3. **Response Time**
   - Expected: < 2s for qualification
   - Alert if: > 5s

4. **Database Connections**
   - Expected: < 10 concurrent
   - Alert if: > 20

#### Monitoring Commands

```bash
# Watch logs in real-time
railway logs --follow

# Check error rate
railway logs | grep "ERROR" | wc -l

# Check ABM campaign rate
railway logs | grep "ABM Campaign initiated" | wc -l
```

## Rollback Plan

### If Issues Detected

1. **Immediate Rollback**:
   ```bash
   # Revert to previous commit
   git revert HEAD
   git push origin main
   
   # Or restore from backup
   cp agents/inbound_agent.py.backup_pre_phase4 agents/inbound_agent.py
   cp agents/follow_up_agent.py.backup_pre_phase4 agents/follow_up_agent.py
   git commit -am "Rollback Phase 4 integration"
   git push origin main
   ```

2. **Partial Rollback** (disable ABM only):
   ```python
   # In InboundAgent.forward(), comment out ABM section:
   # if is_qualified and tier in [LeadTier.SCORCHING, LeadTier.HOT, LeadTier.WARM]:
   #     # ABM campaign initiation code
   #     pass
   ```

3. **Database Rollback**:
   ```bash
   # If needed, drop new tables
   psql $DATABASE_URL -c "DROP TABLE IF EXISTS campaigns CASCADE;"
   psql $DATABASE_URL -c "DROP TABLE IF EXISTS touchpoints CASCADE;"
   ```

## Post-Deployment Verification

### Day 1: Initial Monitoring

- [ ] No critical errors in logs
- [ ] ABM campaigns being initiated
- [ ] Emails being sent
- [ ] Database writes successful
- [ ] Slack notifications working

### Day 2-3: Campaign Execution

- [ ] Follow-up emails being sent
- [ ] Colleague research working
- [ ] Multi-contact outreach functioning
- [ ] Response tracking accurate

### Week 1: Performance Review

- [ ] Campaign conversion rate
- [ ] Colleague engagement rate
- [ ] System performance stable
- [ ] No unexpected errors

## Gradual Rollout (Optional)

### Phase 4a: SCORCHING Only

```python
# Enable ABM only for SCORCHING leads
if tier == LeadTier.SCORCHING:
    # initiate ABM
```

### Phase 4b: SCORCHING + HOT

```python
# Enable for SCORCHING and HOT
if tier in [LeadTier.SCORCHING, LeadTier.HOT]:
    # initiate ABM
```

### Phase 4c: Full Rollout

```python
# Enable for all qualified tiers
if tier in [LeadTier.SCORCHING, LeadTier.HOT, LeadTier.WARM]:
    # initiate ABM
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Symptom**: `ImportError: cannot import name 'AccountOrchestrator'`

**Solution**:
```bash
# Verify file exists
ls -la agents/account_orchestrator.py

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt
```

#### 2. Database Connection Errors

**Symptom**: `ValueError: SUPABASE_URL and SUPABASE_KEY must be set`

**Solution**:
```bash
# Verify environment variables in Railway
railway variables

# Set if missing
railway variables set SUPABASE_URL=<url>
railway variables set SUPABASE_KEY=<key>
```

#### 3. Campaign Not Initiating

**Symptom**: No `🎯 ABM Campaign initiated` logs

**Solution**:
```bash
# Check lead tier
railway logs | grep "qualification_tier"

# Verify orchestrator initialization
railway logs | grep "AccountOrchestrator"

# Check for errors
railway logs | grep "ABM.*failed"
```

## Success Criteria

### Technical

- [x] All tests passing
- [x] No breaking changes to existing functionality
- [x] Graceful error handling
- [x] Performance within acceptable limits

### Business

- [ ] ABM campaigns initiated for qualified leads
- [ ] Multi-contact outreach working
- [ ] "Sue, your colleague Dr. XYZ inquired..." emails sent
- [ ] Increased engagement from colleague contacts

## Support

For deployment issues:
1. Check Railway logs
2. Review this guide
3. Check INTEGRATION_GUIDE.md
4. Contact development team

## Next Steps

1. **Week 1**: Monitor and optimize
2. **Week 2**: Analyze campaign performance
3. **Week 3**: A/B test messaging
4. **Month 1**: Full performance review

