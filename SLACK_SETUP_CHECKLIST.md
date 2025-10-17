# ✅ Slack Agent Caller - Setup Checklist

**Estimated Time**: 30 minutes  
**Difficulty**: Medium  
**Result**: Chat with your AI agents via Slack DM!

---

## 📋 **Quick Setup Checklist**

```
┌─────────────────────────────────────────┐
│  SLACK AGENT CALLER SETUP               │
├─────────────────────────────────────────┤
│                                         │
│  [ ] Step 1: Create Slack App           │
│  [ ] Step 2: Enable Event Subscriptions │
│  [ ] Step 3: Add Bot Scopes             │
│  [ ] Step 4: Install to Workspace       │
│  [ ] Step 5: Get Your User ID           │
│  [ ] Step 6: Set Railway Env Vars       │
│  [ ] Step 7: Test with 'help' command   │
│                                         │
└─────────────────────────────────────────┘
```

---

## **Step 1: Create Slack App** ⚙️

### **What to Do**:
1. Go to: https://api.slack.com/apps
2. Click: **"Create New App"**
3. Choose: **"From scratch"**
4. App Name: `Hume AI Assistant`
5. Workspace: Select yours
6. Click: **"Create App"**

### **Success Indicator**:
✅ You see the Slack app settings page

---

## **Step 2: Enable Event Subscriptions** 📡

### **What to Do**:
1. Left sidebar → **"Event Subscriptions"**
2. Toggle **"Enable Events"** → **ON**
3. Request URL: 
   ```
   https://hume-dspy-agent-production.up.railway.app/slack/events
   ```
4. Wait for **✅ Verified** (green checkmark)
5. Scroll to **"Subscribe to bot events"**
6. Add: `app_mention`
7. Add: `message.im`
8. Click: **"Save Changes"**

### **Success Indicators**:
✅ URL shows: **"Verified"** in green  
✅ Two events listed under bot events

### **Troubleshooting**:
❌ **"Failed to verify"**
- Check Railway is running: `railway logs --tail`
- Verify URL is exact (no trailing slash)
- Wait 10 seconds and try again

---

## **Step 3: Add Bot Scopes** 🔐

### **What to Do**:
1. Left sidebar → **"OAuth & Permissions"**
2. Scroll to **"Bot Token Scopes"**
3. Click: **"Add an OAuth Scope"**
4. Add these 4 scopes:
   - `chat:write`
   - `app_mentions:read`
   - `im:history`
   - `channels:history`

### **Success Indicator**:
✅ 4 scopes listed under "Bot Token Scopes"

---

## **Step 4: Install to Workspace** 🚀

### **What to Do**:
1. Still in **"OAuth & Permissions"**
2. Scroll to top
3. Click: **"Install to Workspace"**
4. Review permissions
5. Click: **"Allow"**
6. **COPY** the Bot User OAuth Token (starts with `xoxb-`)

### **Success Indicator**:
✅ Token starts with: `xoxb-`  
✅ Token is 50+ characters long

**⚠️ SAVE THIS TOKEN** - you'll need it in Step 6!

---

## **Step 5: Get Your User ID** 👤

### **What to Do**:
1. In Slack, click your **profile picture** (top right)
2. Click: **"Profile"**
3. Click: **"More"** (three dots)
4. Click: **"Copy member ID"**

### **Success Indicator**:
✅ ID starts with: `U`  
✅ ID is ~11 characters long

**Example**: `U01234ABC56`

**⚠️ SAVE THIS ID** - you'll need it in Step 6!

---

## **Step 6: Set Railway Environment Variables** 🔧

### **Option A: Automated Script** (Recommended)

Run this script in your terminal:
```bash
cd /Users/joshisrael/hume-dspy-agent
./setup_slack_env.sh
```

**What it does**:
1. Prompts for Bot Token (from Step 4)
2. Prompts for User ID (from Step 5)
3. Validates format
4. Sets Railway variables
5. Triggers redeploy

### **Option B: Manual Setup**

```bash
railway variables set SLACK_BOT_TOKEN="xoxb-YOUR-TOKEN-HERE"
railway variables set JOSH_SLACK_DM_CHANNEL="U01234ABC56"
```

Replace with your actual values!

### **Success Indicators**:
✅ Command runs without errors  
✅ See: "Environment variables set!"  
✅ Railway redeploys (check dashboard)

### **Wait Time**:
⏳ 2-3 minutes for Railway to redeploy

---

## **Step 7: Test Your Bot!** 🧪

### **What to Do**:
1. Open Slack
2. In left sidebar, find **"Apps"** section
3. Find: **"Hume AI Assistant"**
4. Click to open DM
5. Type: `help`
6. Press Enter

### **Expected Response**:
```
🎯 Slack Agent Interface - Help

**Call Agents:**
• call research agent
• call inbound agent
• call follow-up agent

**Quick Commands:**
• pipeline status
• research lead: abc-123
• list agents

**Natural Language:**
Just talk to me! I understand:
• "How many HOT leads do we have?"
• "Research John Smith at Big Clinic"
• "What should I focus on today?"
```

### **Success Indicators**:
✅ Bot responds within 2-3 seconds  
✅ Response includes command menu  
✅ No error messages

---

## **🎉 You're Done! Try These Commands:**

### **Quick Tests**:
```
1. help
2. list agents
3. pipeline status
4. How many HOT leads?
```

### **Advanced Tests**:
```
1. call research agent
2. show recent leads
3. What should I focus on today?
```

---

## **🐛 Troubleshooting**

### **Bot Not Responding**

#### **Check 1: Is Bot Online?**
- Look for green dot next to bot name
- If gray: Bot is offline

**Fix**:
```bash
railway logs --tail
```
Look for: `Application startup complete`

#### **Check 2: Are Env Vars Set?**
```bash
railway variables
```
Should show:
- `SLACK_BOT_TOKEN`
- `JOSH_SLACK_DM_CHANNEL`

**Fix**:
Run `./setup_slack_env.sh` again

#### **Check 3: Event Subscriptions Verified?**
- Go back to Slack app settings
- Event Subscriptions → Should show **"Verified"**

**Fix**:
Re-enter URL and save

### **"Command Not Found"**

**Possible Causes**:
- Typo in command
- Wrong format

**Fix**:
- Type: `help` to see exact command formats
- Copy-paste commands from help menu

### **Research Commands Timeout**

**Cause**: Research API keys not set

**Fix**:
```bash
railway variables set CLEARBIT_API_KEY="your-key"
railway variables set APOLLO_API_KEY="your-key"
railway variables set PERPLEXITY_API_KEY="your-key"
```

---

## **📚 Next Steps**

### **Once Working**:
1. ✅ Read command reference: `SLACK_COMMANDS.md`
2. ✅ Try natural language queries
3. ✅ Research a real lead
4. ✅ Check pipeline status
5. ✅ Explore each agent's menu

### **Advanced Features** (Coming Soon):
- [ ] Bulk operations (research all HOT leads)
- [ ] Custom workflows (automation chains)
- [ ] Analytics dashboard (weekly reports)
- [ ] Multi-user support (team access)

---

## **🔗 Resources**

- **Full Documentation**: `docs/SLACK_AGENT_CALLER.md`
- **Command Reference**: `SLACK_COMMANDS.md`
- **Manual Setup**: `SLACK_SETUP_MANUAL.md`
- **Code**: `api/slack_bot.py`

---

## **🎯 Success Metrics**

Your setup is successful when:
- [ ] Bot responds to `help` command
- [ ] `list agents` shows all 4 agents
- [ ] `pipeline status` returns data
- [ ] Natural language works: "How many HOT leads?"
- [ ] Agent menus display: `call research agent`

---

**Ready to talk to your agents? Let's go!** 🚀
