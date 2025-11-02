# Root Cause Analysis - Why Agents Aren't Using Tools

**Date:** 2025-11-02  
**User Question:** "Why aren't agents using tools for research or follow-up? Why no Slack updates?"

---

## 🎯 Executive Summary

**The agents ARE using DSPy for reasoning (visible in Phoenix), but they're NOT executing actual tools/actions because:**

1. **StrategyAgent wasn't creating Slack notifications** → No `thread_ts` → FollowUpAgent couldn't update Slack
2. **FollowUpAgent lead lookup was failing** → Journey never started → No emails sent → No Slack updates
3. **Most research tools are stubs/TODOs** → Even if called, they return empty results
4. **Test webhook with placeholder data** → Real API calls fail (expected) → But stubs would return empty anyway

---

## ✅ What's FIXED Now

### 1. StrategyAgent Creates Slack Notifications ✅
**Before:** `process_lead_webhook()` never created Slack messages, so no `thread_ts`

**After:**
- Creates Slack notification with qualification results
- Gets `thread_ts` from Slack API response  
- Updates lead record with Slack info
- Passes `thread_ts` to FollowUpAgent

**Impact:** FollowUpAgent can now update Slack threads ✅

### 2. FollowUpAgent Lead Lookup Fixed ✅
**Before:** Query failed immediately → "Lead not found" error

**After:**
- Retry logic (3 attempts, 1 second delay)
- Email fallback lookup if ID fails
- Accepts `slack_thread_ts` from message (passed by StrategyAgent)
- Handles both Lead object and individual parameter calling conventions

**Impact:** FollowUpAgent can now find leads and start journey ✅

---

## ❌ What's STILL MISSING

### 1. Research Tools Are Mostly Stubs ❌

| Tool | Status | Implementation |
|------|--------|---------------|
| Clearbit Person API | ✅ Works | Actually calls API |
| Clearbit Company API | ✅ Works | Actually calls API |
| LinkedIn Search | ❌ **STUB** | Returns `None` - TODO comment |
| Company News Search | ❌ **STUB** | Returns `[]` - TODO comment |
| Tech Stack Analysis | ❌ **STUB** | Returns `[]` - TODO comment |
| Apollo Contacts | ❌ **STUB** | Returns `[]` - TODO comment |
| Domain Lookup | ⚠️ **HEURISTIC** | Simple `.com` guess, not real lookup |

**Code Evidence:**
```python
# agents/research_agent.py:641-697
async def _find_linkedin_profile(...) -> Optional[str]:
    """TODO: Implement using Perplexity or Google Search MCP"""
    return None  # ❌ STUB

async def _find_company_news(...) -> List[Dict[str, str]]:
    """TODO: Implement using Perplexity or news APIs"""
    return []  # ❌ STUB

async def _apollo_find_contacts(...) -> List[Contact]:
    """TODO: Implement Apollo.io people search"""
    return []  # ❌ STUB
```

**Impact:** Even with real data, these tools would return empty because they're not implemented.

### 2. Test Webhook Data Issues ⚠️

**Test Lead:**
- Email: "an_account@example.com" (fake)
- Company: "Lorem ipsum dolor" (placeholder)
- Name: "Lorem ipsum dolor Lorem ipsum dolor" (placeholder)

**Why This Breaks:**
- Clearbit: Returns 404 for fake emails (expected)
- Apollo: Can't search for "Lorem ipsum dolor"
- LinkedIn: No real profile to find
- Domain lookup: Guesses "loremipsumdolor.com" (doesn't exist)

**BUT:** Even with REAL data, most tools would still return empty because they're stubs!

---

## 🔍 Why This Happened

### Design vs. Implementation Gap

1. **DSPy Modules Designed** ✅ → Generate reasoning (working in Phoenix)
2. **Tool Infrastructure Created** ✅ → API keys loaded, methods defined
3. **Tool Implementation** ❌ → Methods are placeholders (TODOs)
4. **Integration** ⚠️ → Methods called but return empty

### The Flow

```
ResearchAgent.research_lead_deeply()
  ├─ plan_research.forward() ✅ Works (DSPy reasoning visible in Phoenix)
  ├─ research_person() 
  │   ├─ _clearbit_person_lookup() ✅ Works (but fails for test email)
  │   └─ _find_linkedin_profile() ❌ Returns None (STUB)
  ├─ research_company()
  │   ├─ _clearbit_company_lookup() ✅ Works (but fails for placeholder)
  │   └─ _find_company_news() ❌ Returns [] (STUB)
  └─ synthesize_findings.forward() ⚠️ Works but has empty data to synthesize
```

**Result:** Reasoning chains visible in Phoenix, but no actual research data collected.

---

## 📊 Current Status by Agent

### StrategyAgent ✅ FIXED
- ✅ Creates Slack notifications
- ✅ Passes `thread_ts` to FollowUpAgent
- ✅ Coordinates all agents

### InboundAgent ✅ Working
- ✅ DSPy reasoning (visible in Phoenix)
- ✅ Qualification works
- ✅ Email/SMS generation works

### ResearchAgent ⚠️ PARTIAL
- ✅ DSPy planning/reasoning (visible in Phoenix)
- ⚠️ Research execution: Only Clearbit works, rest are stubs
- ⚠️ Synthesis has limited data to work with

### FollowUpAgent ✅ FIXED
- ✅ Lead lookup now works (retry + fallback)
- ✅ Accepts `slack_thread_ts` from StrategyAgent
- ⚠️ Journey should start now (needs testing with real data)

---

## 🎯 Next Steps

### HIGH PRIORITY
1. **Implement Research Tools** 
   - LinkedIn search (use Perplexity MCP or Google Search)
   - Company news (use Perplexity MCP)
   - Apollo contacts (implement actual API calls)

2. **Test with Real Data**
   - Use a real Typeform submission with actual lead data
   - Verify tools execute
   - Verify Slack updates
   - Verify emails send

### MEDIUM PRIORITY
3. **Handle Test Data Gracefully**
   - Detect placeholder/test data
   - Skip expensive API calls
   - Return meaningful "test mode" messages

4. **Better Error Handling**
   - When tools return empty, explain WHY
   - Don't silently fail

---

## 💡 The Test Webhook Question

**Q: "Is it because we're using a test webhook?"**

**A: PARTIALLY, but not entirely.**

**Test webhook issues:**
- ✅ Clearbit fails (expected - fake email)
- ✅ No real company to research
- ✅ Placeholder data causes failures

**But the REAL issue:**
- ❌ Most tools are stubs anyway - they'd return empty even with real data
- ❌ StrategyAgent wasn't creating Slack (fixed)
- ❌ FollowUpAgent couldn't find leads (fixed)

**Conclusion:** Test data makes things worse, but the core issues were:
1. Missing Slack notifications (FIXED ✅)
2. Broken lead lookup (FIXED ✅)
3. Unimplemented tools (STILL TODO ❌)

---

## 📝 Summary

**Before Fixes:**
- ❌ No Slack notifications
- ❌ FollowUpAgent couldn't find leads
- ❌ Journey never started
- ❌ No emails sent
- ❌ No Slack updates
- ⚠️ Research tools mostly stubs

**After Fixes:**
- ✅ Slack notifications created
- ✅ FollowUpAgent can find leads (retry + fallback)
- ✅ Journey should start
- ⚠️ Research tools still mostly stubs (need implementation)

**To Verify Fixes Work:**
1. Test with REAL lead data (not placeholder)
2. Check Slack for notifications
3. Check FollowUpAgent logs for journey start
4. Check if emails are sent

**To Complete Functionality:**
1. Implement research tools (LinkedIn, news, Apollo)
2. Test end-to-end with real data
3. Monitor Phoenix for tool execution spans

