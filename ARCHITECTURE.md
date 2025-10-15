# hume-dspy-agent Architecture

**Intelligent Inbound Lead Routing & Autonomous Follow-up System**

## Overview

This system processes inbound leads from Typeform, qualifies them using AI (DSPy + Claude), and autonomously manages the entire follow-up journey with real-time Slack updates.

---

## Architecture Stack

### Core Framework
- **FastAPI**: Webhook receiver and API endpoints
- **Pydantic**: Data validation and type safety
- **DSPy**: Structured LLM pipelines for lead qualification
- **LangGraph**: Stateful autonomous agent for follow-ups
- **Claude (Anthropic)**: Advanced reasoning and decision-making

### Data & State Management
- **Supabase**: PostgreSQL database for lead storage
- **Redis**: State persistence and task queue
- **Celery**: Scheduled follow-up tasks

### Integrations
- **Typeform**: Inbound lead forms
- **Slack**: Real-time team notifications with threading
- **GMass**: Email outreach and follow-ups
- **Close CRM**: Lead sync (optional)

---

## System Flow

```
┌──────────────┐
│   Typeform   │ Lead submits form
│   Webhook    │
└──────┬───────┘
       │
       ↓
┌──────────────────────────────────────────────────────┐
│              FastAPI Webhook Receiver                 │
│  /webhooks/typeform (with signature verification)    │
└──────┬───────────────────────────────────────────────┘
       │
       ├─→ Step 1: Pydantic Validation
       │   └─→ TypeformWebhookPayload model
       │
       ├─→ Step 2: Lead Transformation
       │   └─→ Form-agnostic Lead model
       │
       ├─→ Step 3: DSPy AI Qualification
       │   ├─→ Business Fit Analysis
       │   ├─→ Engagement Analysis
       │   ├─→ Scoring (0-100)
       │   └─→ Tier Assignment (HOT/WARM/COLD/UNQUALIFIED)
       │
       ├─→ Step 4: Slack Notification (with thread creation)
       │   └─→ Returns (channel_id, thread_ts)
       │
       ├─→ Step 5: LangGraph Autonomous Agent START
       │   ├─→ Assess Lead (determine cadence based on tier)
       │   ├─→ Send Initial Email (if qualified)
       │   ├─→ Update Slack Thread ("✅ Email sent, waiting...")
       │   └─→ Schedule Follow-up (via Celery)
       │
       ├─→ Step 6: Supabase Storage
       │   └─→ Save lead + qualification results
       │
       └─→ Step 7: Close CRM Sync (optional)
```

---

## LangGraph Autonomous Agent

### State Machine

The follow-up agent operates as a state machine with persistent memory:

```
         ┌─────────────┐
         │ ASSESS_LEAD │ (Determine strategy based on tier)
         └──────┬──────┘
                │
         ┌──────▼──────────┐
         │ Should Send     │
         │ Initial Email?  │
         └───┬─────────┬───┘
       YES   │         │   NO
             ↓         ↓
    ┌────────────┐  ┌─────────────┐
    │ SEND_EMAIL │  │ UPDATE_SLACK│
    └─────┬──────┘  └──────┬──────┘
          │                │
          └────────┬───────┘
                   ↓
         ┌─────────────────┐
         │  UPDATE_SLACK   │
         │  (Thread Reply) │
         └────────┬────────┘
                  ↓
         ┌─────────────────┐
         │ WAIT_FOR_       │
         │ RESPONSE        │ (Celery scheduled task)
         └────────┬────────┘
                  │
         ┌────────▼──────────┐
         │ Response Status?  │
         └┬────────┬─────────┬┘
    RESPONDED│  NO RESPONSE  │  MAX FOLLOW-UPS
          │        │ CONTINUE │  REACHED
          ↓        ↓          ↓
   ┌──────────┐ ┌────────┐ ┌──────────┐
   │ ESCALATE │ │FOLLOW  │ │MARK_COLD │
   │ HOT_LEAD │ │UP EMAIL│ │          │
   └──────────┘ └───┬────┘ └──────────┘
                    │
                    └─→ UPDATE_SLACK → WAIT_FOR_RESPONSE
                        (Loop continues)
```

### Agent Behaviors by Tier

| Tier | Cadence | Max Follow-ups | Auto-Escalate |
|------|---------|----------------|---------------|
| 🔥 HOT | 4 hours | 5 | Yes (on response) |
| 🌤️ WARM | 24 hours | 3 | Yes (on response) |
| ❄️ COLD | 48 hours | 2 | No |
| ⚠️ UNQUALIFIED | None | 0 | No |

### Slack Thread Updates

Each lead gets its own Slack thread with autonomous updates:

**Initial Message:**
```
🔥 New HOT Lead: John Doe

Email: john@example.com
Score: 85/100
Tier: HOT

Summary:
[AI qualification reasoning]

Autonomous agent will begin follow-up sequence...
```

**Thread Reply 1 (after email sent):**
```
✅ Initial outreach email sent to John
⏳ Waiting for response...
```

**Thread Reply 2 (4 hours later, no response):**
```
📧 Follow-up #1 sent to John
⏱️ Last contact: 0h ago
⏳ Next follow-up in 4h
```

**Thread Reply 3 (lead responds):**
```
🔥🔥🔥 HOT LEAD RESPONSE RECEIVED! 🔥🔥🔥

John (john@example.com) has responded!

Tier: HOT
Follow-ups sent: 1

@channel - Someone should reach out ASAP!
```

**Thread Reply 4 (max follow-ups reached):**
```
❄️ Lead marked as COLD: John

Total follow-ups sent: 5
No response received after 5 attempts.

Moving to nurture campaign.
```

---

## Key Components

### 1. Lead Qualification (DSPy)

**File:** `agents/inbound_agent.py`

Uses DSPy's Chain-of-Thought reasoning to:
- Analyze business fit (company size, patient volume, industry)
- Analyze engagement (form completion, calendly booking, response quality)
- Calculate multi-criteria score (0-100)
- Generate personalized email/SMS templates
- Recommend next actions

**Scoring Breakdown:**
- Business Size: 0-20 points
- Patient Volume: 0-20 points
- Industry Fit: 0-15 points
- Response Completeness: 0-15 points
- Calendly Booking: 0-10 points
- Response Quality: 0-10 points
- Company Data: 0-10 points

**Total:** 100 points possible

### 2. Autonomous Follow-up Agent (LangGraph)

**File:** `agents/follow_up_agent.py`

Manages the entire lead lifecycle:
- **State Persistence:** Uses LangGraph's MemorySaver for persistent state
- **Conditional Logic:** Smart routing based on lead behavior
- **Scheduled Tasks:** Integrates with Celery for time-based actions
- **Error Handling:** Graceful degradation with error logging

### 3. Slack Client (Threading)

**File:** `utils/slack_client.py`

Provides thread-aware Slack updates:
- `post_initial_message()`: Creates new thread, returns (channel, thread_ts)
- `post_thread_reply()`: Posts updates to existing thread
- Supports emoji-based tier indicators
- Markdown formatting for readability

### 4. Email Client (GMass)

**File:** `utils/email_client.py`

Handles email outreach:
- Template-based emails (initial_outreach, follow_up_1, follow_up_2, etc.)
- Tracking (opens, clicks)
- Custom headers for lead attribution
- Tier-aware messaging

---

## Data Models

### Lead Status Lifecycle

```
NEW → CONTACTED → AWAITING_RESPONSE → FOLLOWING_UP
                                             ↓
                                    ┌────────┴────────┐
                                    ↓                 ↓
                               RESPONDED           COLD
                                    ↓
                               QUALIFIED
                                    ↓
                               CONVERTED
```

### Lead Tiers

- **HOT** (≥80 points): High-value, immediate action required
- **WARM** (≥60 points): Qualified, standard follow-up
- **COLD** (≥40 points): Low priority, minimal follow-up
- **UNQUALIFIED** (<40 points): No follow-up

---

## Configuration

### Required Environment Variables

```bash
# Core Services
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Webhooks & Security
TYPEFORM_WEBHOOK_SECRET=your_webhook_secret

# Integrations
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=inbound-leads
GMASS_API_KEY=your_gmass_key

# Infrastructure
REDIS_URL=redis://localhost:6379/0

# Optional
FROM_EMAIL=hello@yourcompany.com
ENVIRONMENT=production
DEBUG=false
```

### Railway Deployment

1. **Add Redis Add-on** in Railway dashboard
2. **Set Environment Variables** in Railway settings
3. **Deploy:**
   ```bash
   railway up
   ```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -d -p 6379:6379 redis:latest

# Start Celery worker (in separate terminal)
celery -A celery_app worker --loglevel=info

# Start Celery beat scheduler (in separate terminal)
celery -A celery_app beat --loglevel=info

# Start FastAPI server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoints

### Webhooks

**POST /webhooks/typeform**
- Receives Typeform webhook events
- Validates signature (HMAC)
- Triggers qualification + follow-up flow

**POST /webhooks/slack**
- Receives Slack events (future: detect responses)

### Management

**POST /qualify** (manual qualification)
```json
{
  "email": "john@example.com",
  "first_name": "John",
  "company": "Acme Inc",
  ...
}
```

**GET /health**
- Health check endpoint

---

## Future Enhancements

### Phase 1 (Current)
- ✅ DSPy qualification
- ✅ LangGraph autonomous agent
- ✅ Slack threading
- ✅ Email follow-ups

### Phase 2 (Planned)
- [ ] Response detection via email parsing
- [ ] SMS follow-ups (Twilio integration)
- [ ] A/B testing email templates
- [ ] Lead scoring model training

### Phase 3 (Future)
- [ ] Voice call integration (Hume EVI)
- [ ] Multi-channel orchestration
- [ ] Predictive lead scoring
- [ ] Revenue attribution tracking

---

## Monitoring & Debugging

### Logs

All components log to standard output with structured format:

```
[2025-10-15 14:30:45] INFO - ✅ DSPy qualification complete
[2025-10-15 14:30:45] INFO -    Score: 85/100
[2025-10-15 14:30:45] INFO -    Tier: HOT
[2025-10-15 14:30:46] INFO - ✅ Autonomous follow-up agent started for lead abc-123
[2025-10-15 14:30:46] INFO -    Journey state: CONTACTED
```

### Debugging Agent State

```python
from agents.follow_up_agent import FollowUpAgent

agent = FollowUpAgent()
config = {"configurable": {"thread_id": "lead-id-here"}}
state = agent.graph.get_state(config)
print(state.values)
```

### Celery Task Status

```bash
# View active tasks
celery -A celery_app inspect active

# View scheduled tasks
celery -A celery_app inspect scheduled

# Revoke a task
celery -A celery_app control revoke task-id
```

---

## Security Considerations

- ✅ Webhook signature verification (HMAC)
- ✅ No hardcoded credentials
- ✅ Environment variable validation
- ✅ Fail-closed security (reject unsigned webhooks)
- ✅ PII redaction in logs (implemented)
- ⚠️ Rate limiting (TODO)
- ⚠️ Request size limits (TODO)

---

## Contributing

When adding new features:

1. **Maintain form-agnostic design** - Don't hardcode field names
2. **Update state machine** - Document new states in LeadStatus enum
3. **Add logging** - Use structured logging with emojis
4. **Test Slack threading** - Ensure thread replies work correctly
5. **Update this document** - Keep architecture docs in sync

---

**Last Updated:** October 15, 2025
**Version:** 2.0.0 (LangGraph Autonomous Agent)
