# 🎯 Slack Agent Caller - Personal AI Interface

Talk to your agents directly through Slack DM!

---

## **🚀 Quick Start**

### **Option 1: Slack Agent Caller** (Recommended - 30 min setup)
Interactive Slack interface to call and test any agent

### **Option 2: Test Email** (Instant - 5 min)
Quick test by sending email to buildoutinc@gmail.com

---

## **🎯 Option 1: Slack Agent Caller**

### **What You Get**

Chat with your agents via Slack DM like this:

```
You: call research agent

Bot: 🔍 Research Agent - Connected

Available Commands:
1️⃣ Research Person
   research person: John Smith at Big Clinic
   
2️⃣ Research Company
   research company: Wellness Clinic Inc
   
3️⃣ Find Contacts
   find contacts at: Big Medical Group

What would you like to research?

You: research person: Dr. Sarah at Wellness Clinic

Bot: 🔍 Research Task Started
Lead: Dr. Sarah Johnson
Company: Wellness Clinic
Task ID: person-research-20251017123456

I'll notify you when complete!
⏱️ ETA: ~30 seconds
```

### **Supported Commands**

#### **Call Agents**
```
call research agent
call inbound agent  
call follow-up agent
```

#### **Quick Commands**
```
pipeline status           → Show current pipeline
research lead: abc-123    → Research specific lead
list agents              → Show all available agents
help                     → Show all commands
```

#### **Natural Language** (Strategy Agent)
```
How many HOT leads do we have?
What should I focus on today?
Show me yesterday's activity
Give me recommendations
```

### **Setup (30 minutes)**

#### **Step 1: Create Slack App**

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name: "Hume AI Assistant"
4. Workspace: Your workspace
5. Click "Create App"

#### **Step 2: Configure Bot**

**Enable Event Subscriptions:**
1. Go to "Event Subscriptions"
2. Toggle "Enable Events" ON
3. Request URL: `https://hume-dspy-agent-production.up.railway.app/slack/events`
4. Subscribe to bot events:
   - `app_mention`
   - `message.im` (for DMs)
5. Save Changes

**Add Bot Scopes:**
1. Go to "OAuth & Permissions"
2. Add these scopes:
   - `chat:write`
   - `channels:history`
   - `im:history`
   - `app_mentions:read`
3. Install to Workspace
4. Copy "Bot User OAuth Token" (starts with `xoxb-`)

#### **Step 3: Get Your User ID**

1. In Slack, click your profile
2. "More" → "Copy member ID"
3. Save this (format: `U123ABC456`)

#### **Step 4: Set Railway Variables**

```bash
railway variables set SLACK_BOT_TOKEN="xoxb-your-token-here"
railway variables set JOSH_SLACK_DM_CHANNEL="U123ABC456"  # Your user ID
```

#### **Step 5: Test It!**

1. Open Slack
2. Find "Hume AI Assistant" in Apps
3. Send a DM: `help`
4. You should get a response!

**First Commands to Try:**
```
help
list agents
call research agent
pipeline status
```

---

## **📧 Option 2: Test Email (Instant)**

### **Quick Test - Send Email to buildoutinc@gmail.com**

This submits a test lead that will:
1. ✅ Qualify as HOT (perfect ICP fit)
2. ✅ Send email via GMass
3. ✅ Post to Slack #inbound-leads

### **Run Test**

```bash
cd /Users/joshisrael/hume-dspy-agent

# Set environment
export API_ENDPOINT="https://hume-dspy-agent-production.up.railway.app"
export TYPEFORM_WEBHOOK_SECRET="your-webhook-secret"

# Run test
python test_email_webhook.py
```

### **What It Does**

**Creates Test Lead:**
- **Email**: buildoutinc@gmail.com
- **Name**: Build Out
- **Company**: Wellness Clinic
- **Patients**: 200-300
- **Use Case**: Weight loss clinic with 200+ patients
- **Calendly**: Booked ✅

**Expected Flow:**
1. Webhook submitted → 200 OK
2. Lead qualified as **HOT** (high score)
3. Email sent via GMass
4. Slack notification posted
5. Lead stored in Supabase

**Check Results:**
- 📧 **Email**: Check buildoutinc@gmail.com (30-60 seconds)
- 💬 **Slack**: Check #inbound-leads channel
- 📊 **GMass**: [https://www.gmass.co/app/campaigns](https://www.gmass.co/app/campaigns)
- 🗄️ **Supabase**: Check `leads` table

### **Example Output**

```
🧪 Test Email + Webhook Submission
======================================================================

📤 Submitting test webhook...

**Test Lead Details:**
   Email: buildoutinc@gmail.com
   Name: Build Out
   Company: Wellness Clinic
   Patients: 200-300
   Use Case: Weight loss clinic with 200+ patients
   Calendly Booked: Yes

**Expected Qualification:**
   Tier: HOT or SCORCHING (high score)
   Reason: Perfect ICP fit + Calendly booking
   Email: Will be sent via GMass

📡 Response Status: 200

✅ Webhook accepted successfully!

**What happens next:**
   1. ✅ Raw event stored in Supabase
   2. ⏳ Background processing started
   3. ⏳ Lead qualification (DSPy agent)
   4. ⏳ Slack notification sent
   5. ⏳ Email sent via GMass

**Check:**
   📧 Email: Check buildoutinc@gmail.com inbox
   💬 Slack: Check your #inbound-leads channel
   📊 GMass: Check https://www.gmass.co/app/campaigns
   🗄️ Supabase: Check 'leads' table
```

---

## **📊 Comparison**

| Feature | Option 1: Slack Caller | Option 2: Test Email |
|---------|------------------------|----------------------|
| **Setup Time** | 30 minutes | 5 minutes |
| **Interactivity** | ✅ Full chat interface | ❌ One-shot test |
| **Test All Agents** | ✅ Yes | ❌ Only inbound |
| **Ongoing Use** | ✅ Daily tool | ❌ Testing only |
| **Natural Language** | ✅ Yes | ❌ No |
| **Real-time Feedback** | ✅ Yes | ⏳ Wait 30-60s |

### **Recommendation**

**For Testing**: Use Option 2 first (quick validation)  
**For Daily Use**: Set up Option 1 (better experience)

---

## **🎯 Slack Agent Caller - Full Command Reference**

### **Research Agent Commands**

```
call research agent

# Then use:
research person: [name] at [company]
research company: [company name]
find contacts at: [company]
research lead: [lead-id]
```

**Examples:**
```
research person: Dr. Sarah Johnson at Wellness First
research company: Big Medical Clinic
find contacts at: Wellness First
research lead: abc-123-def-456
```

### **Inbound Agent Commands**

```
call inbound agent

# Then use:
show recent leads
explain score for lead: [id]
requalify lead: [id]
test qualification: [data]
```

**Examples:**
```
show recent leads
explain score for lead: abc-123-def-456
requalify lead: abc-123-def-456
```

### **Follow-Up Agent Commands**

```
call follow-up agent

# Then use:
show followup for lead: [id]
send followup now to: [id]
pause followup for: [id]
escalate lead: [id]
```

**Examples:**
```
show followup for lead: abc-123-def-456
send followup now to: abc-123-def-456
pause followup for: abc-123-def-456
escalate lead: abc-123-def-456
```

### **Quick Commands (No Agent Call Needed)**

```
pipeline status        → Current pipeline metrics
list agents           → Show all agents
help                  → Show all commands
```

### **Natural Language (Strategy Agent)**

Just talk naturally!

```
How many HOT leads do we have?
What should I focus on today?
Show me recent activity
Give me recommendations
What are my priorities?
```

---

## **🧪 Testing Workflow**

### **Quick Test (Option 2)**

```bash
# 1. Send test email
python test_email_webhook.py

# 2. Wait 60 seconds

# 3. Check results
# - Email at buildoutinc@gmail.com
# - Slack notification
# - GMass campaign
```

### **Full Test (Option 1)**

```bash
# 1. Set up Slack bot (one-time, 30 min)

# 2. Send DM to bot: "help"

# 3. Try each agent:
call research agent
→ research person: Test User at Test Co

call inbound agent  
→ show recent leads

call follow-up agent
→ show active sequences

# 4. Try quick commands:
pipeline status
list agents

# 5. Try natural language:
How many HOT leads do we have?
What should I focus on?
```

---

## **🐛 Troubleshooting**

### **Slack Bot Not Responding**

**Check:**
1. Event Subscriptions enabled
2. Request URL verified: `/slack/events`
3. Bot scopes configured
4. Railway variables set:
   - `SLACK_BOT_TOKEN`
   - `JOSH_SLACK_DM_CHANNEL`

**Test:**
```bash
# Check Railway logs
railway logs

# Test endpoint
curl https://hume-dspy-agent-production.up.railway.app/slack/events
```

### **Test Email Not Sending**

**Check:**
1. GMass API key set
2. FROM_EMAIL configured
3. Webhook secret correct

**Test:**
```bash
# Run GMass test
python test_gmass.py

# Check Railway logs
railway logs | grep "GMass"
```

### **A2A Commands Failing**

**Check:**
1. A2A_API_KEY set
2. Introspection service running

**Test:**
```bash
curl -X POST https://hume-dspy-agent-production.up.railway.app/a2a/introspect \
  -H "Authorization: Bearer YOUR_A2A_KEY" \
  -H "Content-Type: application/json" \
  -d '{"mode":"query","agent_type":"inbound","action":"show_state"}'
```

---

## **📁 Files Created**

```
api/slack_bot.py               (Slack bot implementation)
test_email_webhook.py          (Test email script)
docs/SLACK_AGENT_CALLER.md     (This documentation)
```

---

## **🚀 Next Steps**

### **After Setup**

1. **Daily Use**:
   ```
   # Morning check
   pipeline status
   
   # Throughout day
   research lead: [new-lead-id]
   show recent leads
   ```

2. **Deep Dives**:
   ```
   call research agent
   → research company: [prospect]
   
   call inbound agent
   → explain score for lead: [id]
   ```

3. **Strategic Reviews**:
   ```
   What are my top priorities?
   Give me recommendations
   Show me trends
   ```

---

## **✅ Success Criteria**

**Option 1 (Slack) Working When:**
- [x] Bot responds to `help` command
- [x] `call research agent` shows menu
- [x] `pipeline status` returns data
- [x] Natural language queries work

**Option 2 (Email) Working When:**
- [x] Test script runs successfully
- [x] Email arrives at buildoutinc@gmail.com
- [x] Slack notification posted
- [x] GMass campaign appears

---

**Summary**: You now have two ways to test and interact with your agents - an interactive Slack interface for daily use, or a quick email test for validation. Choose based on your immediate needs! 🚀
