# 📅 Follow-Up Email Scheduling (TODO)

**Date**: October 18, 2025  
**Priority**: MEDIUM  
**Status**: Follow-ups currently disabled to prevent spam

---

## **Current State**

### **What Works** ✅
- Initial email sent immediately after lead qualification
- Slack notification posted
- Lead saved to database

### **What's Disabled** ⚠️
- **Follow-up emails are NOT sent automatically**
- Workflow ENDs after initial email
- No scheduling system in place

---

## **Why Follow-Ups Are Disabled**

**Problem**: The original LangGraph workflow sent ALL emails immediately:

```
05:05:04 - ✅ Email sent: initial_outreach
05:05:12 - ✅ Email sent: follow_up_1    ← 8 seconds later!
05:05:17 - ❌ Email sent: follow_up_2    ← 13 seconds later!
```

**This caused**:
- Email spam (3 emails in 18 seconds!)
- GMass limit exhaustion
- Poor user experience
- Potential spam reports

**Fix Applied**: Workflow now ENDS after initial email.

---

## **Ideal Follow-Up Cadence**

Based on tier:

| Tier | Cadence | Max Attempts | Total Duration |
|------|---------|--------------|----------------|
| **HOT** | 12 hours | 5 | 2.5 days |
| **WARM** | 24 hours | 4 | 4 days |
| **COOL** | 48 hours | 3 | 6 days |
| **COLD** | 72 hours | 2 | 6 days |

**Example for WARM lead**:
```
Day 0: Initial outreach (immediate)
Day 1: Follow-up #1 (24h later)
Day 2: Follow-up #2 (48h later)
Day 3: Follow-up #3 (72h later)
Day 4: Follow-up #4 (96h later) → Mark as COLD if no response
```

---

## **How to Implement Scheduling**

### **Option 1: Railway Cron Jobs** (Recommended)

**Pros**:
- Built into Railway
- No external dependencies
- Simple setup

**Cons**:
- Limited to hourly/daily intervals
- Not as flexible as Celery

**Implementation**:

1. **Create cron endpoint** (`api/cron.py`):
```python
from fastapi import APIRouter

router = APIRouter(prefix="/cron", tags=["cron"])

@router.post("/process-follow-ups")
async def process_pending_follow_ups():
    """Check for leads needing follow-ups and send them."""
    
    # Query Supabase for leads where:
    # - status = 'awaiting_response'
    # - last_email_sent_at + cadence_hours < now()
    
    from api.main import follow_up_agent, supabase
    
    # Example query
    leads_ready = supabase.table('leads').select('*').eq(
        'status', 'awaiting_response'
    ).execute()
    
    for lead in leads_ready.data:
        # Check if enough time has passed
        # If yes: follow_up_agent.continue_lead_journey(lead_id)
        pass
    
    return {"ok": True, "leads_processed": len(leads_ready.data)}
```

2. **Set up Railway cron**:
```bash
# In Railway dashboard:
# Settings → Cron Jobs → Add Job
# Path: /cron/process-follow-ups
# Schedule: 0 */6 * * *  (every 6 hours)
```

---

### **Option 2: Celery Beat** (More Powerful)

**Pros**:
- Precise scheduling (e.g., "24 hours from now")
- Can handle complex workflows
- Battle-tested for background jobs

**Cons**:
- Requires Redis
- More complex setup
- Additional Railway service

**Implementation**:

1. **Add dependencies**:
```bash
pip install celery redis
```

2. **Create Celery app** (`celery_app.py`):
```python
from celery import Celery

app = Celery('hume_agent', broker='redis://localhost:6379/0')

@app.task
def send_follow_up(lead_id: str):
    from api.main import follow_up_agent
    follow_up_agent.continue_lead_journey(lead_id)

# Schedule task when initial email sent
send_follow_up.apply_async(args=[lead_id], countdown=86400)  # 24 hours
```

3. **Deploy Celery worker to Railway**

---

### **Option 3: Supabase Edge Functions** (Serverless)

**Pros**:
- Serverless (no extra costs)
- Integrated with your database
- Can trigger on database changes

**Cons**:
- Requires Supabase Pro ($25/mo)
- Learning curve

**Implementation**: Use Supabase Functions to check for pending follow-ups.

---

## **Recommended Approach**

**Phase 1** (Quick fix - TODAY):
1. ✅ Keep workflow ending after initial email (spam prevention)
2. ✅ Upgrade GMass
3. ⏳ Manually trigger follow-ups for now (if needed)

**Phase 2** (Next week):
1. Implement Railway cron job
2. Query Supabase for leads ready for follow-up
3. Call `follow_up_agent.continue_lead_journey(lead_id)`

**Phase 3** (Later):
1. Consider Celery if you need more precision
2. Add email response detection (webhook from Gmail)
3. Implement engagement scoring

---

## **Code Changes Needed**

### **1. Track last email time in database**

Add to Supabase `leads` table:
```sql
ALTER TABLE leads ADD COLUMN last_email_sent_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN next_follow_up_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN follow_up_count INTEGER DEFAULT 0;
```

### **2. Update agent to save timestamps**

```python
# In follow_up_agent.py send_initial_email()
state['email_sent_at'] = datetime.utcnow().isoformat()
state['next_follow_up_at'] = (
    datetime.utcnow() + timedelta(hours=state['next_follow_up_hours'])
).isoformat()

# Save to database
supabase.table('leads').update({
    'last_email_sent_at': state['email_sent_at'],
    'next_follow_up_at': state['next_follow_up_at']
}).eq('id', state['lead_id']).execute()
```

### **3. Create cron endpoint**

```python
@router.post("/cron/process-follow-ups")
async def process_follow_ups():
    now = datetime.utcnow()
    
    # Get leads ready for follow-up
    ready = supabase.table('leads').select('*').lt(
        'next_follow_up_at', now.isoformat()
    ).eq('status', 'awaiting_response').execute()
    
    count = 0
    for lead in ready.data:
        follow_up_agent.continue_lead_journey(
            lead_id=lead['id'],
            response_received=False
        )
        count += 1
    
    return {"processed": count}
```

---

## **Testing Plan**

1. **Upgrade GMass** ✅
2. **Test initial email** (should work)
3. **Verify workflow ENDS** (no immediate follow-ups)
4. **Implement cron job** (Phase 2)
5. **Test cron manually**: `curl POST /cron/process-follow-ups`
6. **Monitor for 48 hours** (ensure follow-ups trigger correctly)

---

## **Next Steps**

**Immediate**:
- [x] Fix email spam (workflow ends after initial)
- [ ] Upgrade GMass
- [ ] Test initial email sending

**This Week**:
- [ ] Add timestamp columns to database
- [ ] Create cron endpoint
- [ ] Set up Railway cron job (every 6 hours)

**Next Week**:
- [ ] Monitor follow-up success rates
- [ ] Consider Celery if more precision needed
- [ ] Add email response detection

---

**Current status**: Follow-ups disabled, initial emails working. Scheduling to be implemented in Phase 2.
