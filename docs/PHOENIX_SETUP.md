# 🔭 Phoenix Observability Setup

**Phoenix** gives you complete visibility into what your DSPy agents are actually doing.

---

## **What Phoenix Provides**

### **Full Visibility** 👁️
- **Every DSPy call traced** - See exactly what prompts are sent to Claude
- **Every LLM interaction** - Input/output, tokens used, latency
- **Agent behavior** - Understand decision-making flow
- **Error tracking** - See where and why things fail

### **Real-Time Monitoring** 📊
- **Token usage tracking** - Know exactly how much you're spending
- **Latency monitoring** - See which calls are slow
- **Success rates** - Track how often agents succeed vs fail
- **Cost analysis** - Break down costs by agent, model, task type

### **Debugging** 🐛
- **Trace visualization** - Visual tree of agent calls
- **Span details** - See inputs/outputs at every step
- **Error traces** - Complete stack traces with context
- **Replay traces** - Understand what went wrong

---

## **Setup (5 Minutes)**

### **1. Get API Key**

1. Go to: https://app.phoenix.arize.com/
2. Sign in (or create account)
3. Go to **Settings** → **API Keys**
4. Create a **System API Key**
5. Copy the key

---

### **2. Install Dependencies**

```bash
pip install -r requirements.txt
```

This installs:
- `arize-phoenix-otel` - Phoenix tracing
- `openinference-instrumentation-dspy` - DSPy instrumentation
- `opentelemetry-api` and `opentelemetry-sdk` - OpenTelemetry

---

### **3. Add to Railway Environment**

In Railway dashboard:
1. Go to your **hume-dspy-agent** service
2. Click **Variables** tab
3. Add these variables:

```bash
PHOENIX_API_KEY=your_actual_phoenix_api_key_here
PHOENIX_PROJECT_NAME=hume-dspy-agent
PHOENIX_ENDPOINT=https://app.phoenix.arize.com/s/buildoutinc/v1/traces
```

4. Click **Deploy** to restart with new variables

---

### **4. Verify It Works**

After deployment, check Railway logs:

**✅ Success**:
```
🔭 Initializing Phoenix observability...
✅ Phoenix tracing initialized
   Project: hume-dspy-agent
   Endpoint: https://app.phoenix.arize.com/s/buildoutinc/v1/traces
   Dashboard: https://app.phoenix.arize.com/
✅ DSPy instrumentation enabled
   All DSPy calls will be traced in Phoenix
```

**❌ Not configured**:
```
⚠️ PHOENIX_API_KEY not set - observability disabled
```

---

### **5. View Traces**

1. Go to: https://app.phoenix.arize.com/
2. Select project: **hume-dspy-agent**
3. See all traces from your agents!

---

## **What You'll See in Phoenix**

### **Trace Example: Lead Qualification**

```
webhook_received (200ms)
├─ parse_typeform_data (50ms)
├─ qualify_lead (8.2s)
│  ├─ dspy.ChainOfThought (8.1s)
│  │  ├─ format_prompt (10ms)
│  │  ├─ openrouter_call (8.0s)
│  │  │  ├─ model: claude-haiku-4.5
│  │  │  ├─ input_tokens: 450
│  │  │  ├─ output_tokens: 120
│  │  │  ├─ cost: $0.0023
│  │  │  └─ latency: 8000ms
│  │  └─ parse_response (50ms)
│  └─ validate_tier (100ms)
├─ send_slack_notification (1.2s)
└─ save_to_database (300ms)

Total: 9.95s
Cost: $0.0023
```

### **What This Tells You**:
- **8 seconds** spent on LLM call (expected)
- **450 input tokens** - your prompt
- **120 output tokens** - Claude's response
- **$0.0023** - actual cost of this qualification
- Can see the EXACT prompt sent and response received

---

## **Use Cases**

### **1. Debug Why Agent Is Slow**
**Problem**: Agent takes 15 seconds to respond in Slack

**Phoenix shows**:
```
Strategy Agent Response (15.2s)
├─ DSPy Conversation (12.1s)  ← SLOW!
│  └─ OpenRouter call (12.0s) ← CULPRIT
└─ Format response (3.1s)
```

**Solution**: Reduce prompt size or switch to Haiku for this task

---

### **2. Find Hallucinations**
**Problem**: Agent keeps making up data

**Phoenix shows**:
- Input: "Give me pipeline stats"
- Context: `{"data_access": "NONE", "message": "No Supabase..."}`
- Output: "Pipeline: 28 leads (3 HOT, 8 WARM...)"

**Solution**: See the exact prompt that led to hallucination, fix signature

---

### **3. Track Costs**
**Question**: How much are we spending per lead?

**Phoenix shows**:
- Average cost per qualification: $0.0023
- Average cost per Slack response: $0.015
- Total daily spend: $12.50
- Most expensive: Strategy Agent ($8/day)

**Solution**: Use Haiku for more tasks, reserve Sonnet for complex ones

---

### **4. See Agent Decision Flow**
**Question**: Why didn't agent send follow-up?

**Phoenix trace**:
```
FollowUpAgent (2.1s)
├─ assess_lead (100ms)
│  └─ tier=COOL, cadence=48h
├─ send_initial_email (1.8s)
│  └─ gmass_api_call (1.7s)
└─ check_response_status (200ms)
   └─ decision: END (no follow-up due to workflow change)
```

**Solution**: See exactly where workflow stopped and why

---

## **Advanced: Custom Spans**

You can add custom tracing to your own code:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("custom_operation")
def my_function():
    # Your code here
    pass
```

This will show up in Phoenix traces alongside DSPy calls.

---

## **Troubleshooting**

### **"Phoenix tracing disabled"**
**Solution**: Add `PHOENIX_API_KEY` to Railway environment variables

### **"No traces appearing"**
**Possible causes**:
1. API key invalid - check in Phoenix Settings
2. Project name mismatch - verify in Railway and Phoenix
3. Endpoint wrong - should be `https://app.phoenix.arize.com/s/buildoutinc/v1/traces`
4. Network issue - check Railway logs for connection errors

### **"DSPy instrumentation failed"**
**Solution**: 
```bash
pip install openinference-instrumentation-dspy
```
Re-deploy to Railway

---

## **Cost of Phoenix**

**Free Tier**:
- Up to 1M traces/month
- 30 days retention
- All features included

**Paid Tiers**:
- More traces
- Longer retention
- Team features

**For your scale**: Free tier is MORE than enough

---

## **Benefits for Your Use Case**

### **1. Answer "What's Actually Happening?"**
Instead of guessing why agent does something, you'll SEE:
- Exact prompts sent
- Exact responses received
- Decision points
- Error locations

### **2. Stop Hallucinations**
See the EXACT context agent had when it made up data:
- Was database connected?
- What data was available?
- What did prompt say?

### **3. Optimize Costs**
Track which agents/tasks are expensive:
- Use Haiku for cheap tasks
- Reserve Sonnet for complex reasoning
- See ROI per lead

### **4. Debug Production Issues**
When something breaks in production:
- See complete trace
- Replay the exact scenario
- Understand root cause

---

## **Next Steps**

1. ✅ Add `PHOENIX_API_KEY` to Railway
2. ✅ Deploy
3. ✅ Send test webhook or Slack message
4. ✅ View trace in Phoenix dashboard
5. ✅ Explore trace details

**Dashboard**: https://app.phoenix.arize.com/

---

## **Integration Status**

**Current**:
- ✅ Phoenix SDK installed
- ✅ OpenTelemetry configured
- ✅ DSPy instrumentation enabled
- ✅ Auto-tracing on startup
- ✅ Environment variables documented

**What Gets Traced**:
- ✅ All DSPy calls (ChainOfThought, ReAct, etc.)
- ✅ All LLM calls (OpenRouter, Claude, etc.)
- ✅ Strategy Agent conversations
- ✅ AuditAgent data queries
- ✅ Inbound Agent qualifications
- ✅ Research Agent enrichment
- ✅ Follow-Up Agent email sequences

**What Doesn't Get Traced** (yet):
- ⚠️ Slack API calls (not instrumented)
- ⚠️ GMass API calls (not instrumented)
- ⚠️ Supabase queries (not instrumented)

To trace these, add custom spans (see Advanced section).

---

**Ready to enable Phoenix!** 🚀

Just add the API key to Railway and you'll have complete visibility into your agents.
