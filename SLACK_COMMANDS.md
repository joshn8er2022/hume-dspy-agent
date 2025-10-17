# 🤖 Slack Agent Caller - Command Reference

Quick reference for talking to your AI agents via Slack!

---

## 🎯 **Quick Start Commands**

### **Get Help**
```
help
```
Shows all available commands and agents.

### **List All Agents**
```
list agents
```
Shows: Research, Inbound, Follow-Up, Strategy agents with descriptions.

### **Pipeline Status**
```
pipeline status
```
Shows current lead counts by tier (HOT/WARM/COLD).

---

## 🔍 **Research Agent Commands**

### **Call Research Agent**
```
call research agent
```
Opens Research Agent menu with all available commands.

### **Research a Person**
```
research person: Dr. Sarah Johnson at Wellness Clinic
```
Triggers deep research on a specific person + company.

**Returns**:
- Person profile (Clearbit)
- Company intelligence
- Contact discovery
- LinkedIn data

### **Research a Company**
```
research company: Big Medical Group
```
Researches company only (no specific person).

### **Find Contacts**
```
find contacts at: Wellness First Medical
```
Finds additional contacts at a company.

### **Research by Lead ID**
```
research lead: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Deep research on existing lead from database.

---

## 📥 **Inbound Agent Commands**

### **Call Inbound Agent**
```
call inbound agent
```
Opens Inbound Agent menu.

### **Show Recent Leads**
```
show recent leads
```
Lists latest qualified leads with scores.

### **Explain Score**
```
explain score for lead: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Shows detailed scoring breakdown for a lead.

### **Requalify Lead**
```
requalify lead: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Re-runs qualification on a lead (useful if data changed).

### **Test Qualification**
```
test qualification: [paste lead data JSON]
```
Tests qualification logic on sample data.

---

## 📧 **Follow-Up Agent Commands**

### **Call Follow-Up Agent**
```
call follow-up agent
```
Opens Follow-Up Agent menu.

### **Show Follow-Up State**
```
show followup for lead: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Shows current follow-up sequence status.

**Returns**:
- Current stage (1-8)
- Emails sent count
- Last contact date
- Next scheduled send

### **Send Immediate Follow-Up**
```
send followup now to: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Triggers immediate follow-up email (bypasses schedule).

### **Pause Follow-Up**
```
pause followup for: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Stops follow-up sequence for a lead.

### **Escalate to Human**
```
escalate lead: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee
```
Marks lead for manual human follow-up.

---

## 🎯 **Strategy Agent (Natural Language)**

The Strategy Agent responds to natural language questions!

### **Pipeline Questions**
```
How many HOT leads do we have?
What's our pipeline looking like?
Show me yesterday's activity
```

### **Recommendations**
```
What should I focus on today?
Give me recommendations
What are my top priorities?
```

### **Analytics**
```
Show me conversion rates
What's our qualification success rate?
How many leads this week?
```

### **Strategic Insights**
```
What trends are you seeing?
Which lead sources perform best?
What should I optimize?
```

---

## 💡 **Usage Examples**

### **Morning Check-In**
```
You: Good morning! What should I focus on today?

Bot: 🌅 Good morning!

**Today's Priorities:**
1. 3 HOT leads need immediate follow-up
2. 7 WARM leads in sequence (all on track)
3. Review: 2 leads moved from COLD → WARM (engagement improved)

**Recommended Actions:**
• Call John Smith (HOT, 92/100, calendly booked)
• Review Sarah Johnson (WARM → HOT potential)
• Research: Big Medical Group (2 contacts, high intent)

**Pipeline Health:** ✅ Strong (15 active conversations)
```

### **Research Workflow**
```
You: call research agent

Bot: 🔍 Research Agent - Connected
[Shows menu]

You: research person: Dr. Emily Chen at Metabolic Health Center

Bot: 🔍 Research Task Started
Task ID: person-research-20251017140530
⏱️ ETA: ~30 seconds

[30 seconds later]

Bot: ✅ Research Complete: Dr. Emily Chen

**Person Profile:**
• Role: Medical Director
• LinkedIn: [link]
• Email: emily@metabolichealth.com
• Phone: (555) 123-4567

**Company Intelligence:**
• Size: 50-100 employees
• Revenue: $5M-$10M
• Tech stack: Epic EMR, Athenahealth
• Recent news: Expanded to 3 locations

**Recommended Approach:**
Focus on EMR integration pain points. High intent signal: Recently posted about "better patient tracking tools"
```

### **Lead Follow-Up Check**
```
You: show followup for lead: abc-123-def-456

Bot: 📧 Follow-Up Status: John Smith

**Current State:**
• Stage: 3/8
• Journey: warm
• Last Contact: Oct 15, 2025 (2 days ago)
• Next Scheduled: Oct 18, 2025 (tomorrow)

**Email History:**
1. ✅ Initial outreach (Oct 10) - Opened ✓
2. ✅ Follow-up #1 (Oct 13) - Opened ✓, Clicked ✓
3. ✅ Follow-up #2 (Oct 15) - Sent

**Engagement Score:** 87/100 (High)
**Recommendation:** Strong interest - consider personal call
```

---

## 🚦 **Response Times**

| Command Type | Expected Response |
|--------------|-------------------|
| **Quick commands** (help, list) | Instant |
| **Pipeline status** | 1-2 seconds |
| **Research person** | 30-60 seconds |
| **Research company** | 20-40 seconds |
| **Lead queries** | 2-5 seconds |
| **Follow-up actions** | 5-10 seconds |

---

## 🐛 **Troubleshooting**

### **Bot Not Responding**
**Check**:
1. Is bot online in Slack? (green dot)
2. Did you DM the bot (not post in channel)?
3. Are Railway env vars set?

**Fix**:
```bash
railway logs | grep -i slack
```

### **Command Not Working**
**Tips**:
- Use exact command syntax (case-insensitive but format matters)
- Lead IDs must be full UUID format
- Use quotes for complex data: `"text with spaces"`

### **Research Timing Out**
**Cause**: API keys not configured

**Fix**:
```bash
railway variables set CLEARBIT_API_KEY="your-key"
railway variables set APOLLO_API_KEY="your-key"
railway variables set PERPLEXITY_API_KEY="your-key"
```

---

## 🎯 **Best Practices**

### **Use Natural Language with Strategy Agent**
```
✅ "What should I focus on today?"
✅ "Show me pipeline status"
✅ "How many HOT leads?"

❌ "query_pipeline_status"
❌ "execute command: show_leads"
```

### **Be Specific with Research**
```
✅ "research person: John Smith at ABC Clinic"
✅ "research company: Big Medical Group Inc"

❌ "research john"
❌ "find info on clinic"
```

### **Use Full Lead IDs**
```
✅ show followup for lead: 3c5c0cfa-eee5-4fea-b710-53d6571fdeee

❌ show followup for lead: 3c5c0cfa
```

---

## 📚 **Advanced Usage**

### **Bulk Operations** (Coming Soon)
```
research all HOT leads
send followup to all WARM leads
export pipeline to CSV
```

### **Custom Workflows** (Coming Soon)
```
create workflow: new_hot_lead
  → research lead
  → send personalized email
  → schedule follow-up
  → notify in Slack
```

### **Analytics Dashboard** (Coming Soon)
```
show weekly report
compare this month vs last month
export campaign performance
```

---

## 🔗 **Related Docs**

- **Setup Guide**: `docs/SLACK_AGENT_CALLER.md`
- **API Reference**: `api/slack_bot.py`
- **A2A Protocol**: `agents/introspection.py`

---

## 🎉 **Quick Win Commands**

Try these first:
1. `help` - Get oriented
2. `pipeline status` - See current state
3. `call research agent` - Explore research features
4. `How many HOT leads?` - Test natural language

**Have fun talking to your agents!** 🚀
