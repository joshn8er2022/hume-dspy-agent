# 🔧 ReAct Implementation Plan - Tool Calling for Strategy Agent

**Problem Identified**: ChainOfThought can't call tools  
**Solution**: Implement DSPy ReAct for action-based queries

---

## **🚨 Current Architecture (Broken)**

```python
# Step 1: DSPy generates TEXT response
result = ChainOfThought(StrategyConversation)(
    context=system_context,
    user_message="audit our lead flow",
    conversation_history=history
)

# Step 2: LLM TALKS about querying data
result.response = "Let me query GMass directly right now and get you real metrics..."

# Step 3: Pattern matching detects "audit"
if self._is_audit_request(message):  # Hardcoded!
    audit_result = await self._execute_audit(message)
    return audit_result

# PROBLEM: ChainOfThought never actually called any tools!
# It just SAID it would call them.
```

**Issues**:
1. ❌ ChainOfThought can't execute tools
2. ❌ Relies on brittle pattern matching
3. ❌ Hardcoded audit detection
4. ❌ Can't handle multi-tool scenarios
5. ❌ LLM hallucinates "calling tools" instead of actually calling them

---

## **✅ DSPy ReAct Architecture**

### **What is ReAct?**

**ReAct** = **Reasoning** + **Acting**

It's a DSPy module that can:
1. **Think**: Reason about what to do
2. **Act**: Execute tools/functions
3. **Observe**: See tool results
4. **Think**: Reason about results
5. **Act**: Call more tools if needed
6. **Answer**: Return final response

**Example Flow**:
```
User: "audit our lead flow"

ReAct:
├─ Thought: "User wants audit data. I need to query GMass and Supabase."
├─ Action: audit_lead_flow(timeframe_hours=24)
├─ Observation: {leads: 15, emails: {sent: 42, opened: 18, ...}}
├─ Thought: "I have real data. Format it nicely."
└─ Answer: "📊 Lead Flow Audit (Last 24h):
            - 15 leads captured
            - 42 emails sent
            - 18 opened (42.9%)
            ..."
```

---

## **🔧 Implementation Plan**

### **Phase 1: Define Tools** (30 minutes)

Tools are Python functions that ReAct can call:

```python
# agents/strategy_agent.py

def audit_lead_flow_tool(timeframe_hours: int = 24) -> str:
    """
    Query lead flow data from Supabase and GMass.
    
    Args:
        timeframe_hours: How many hours back to audit
    
    Returns:
        JSON string with audit results
    """
    import asyncio
    audit_data = asyncio.run(self.audit_agent.audit_lead_flow(timeframe_hours))
    return json.dumps(audit_data)


def query_supabase_tool(table: str, filters: dict = None) -> str:
    """
    Query Supabase table.
    
    Args:
        table: Table name (leads, conversations, agent_state)
        filters: Optional filters as dict
    
    Returns:
        JSON string with query results
    """
    # Execute Supabase query
    result = self.supabase.table(table).select("*")
    if filters:
        for key, value in filters.items():
            result = result.eq(key, value)
    data = result.execute()
    return json.dumps(data.data)


def query_gmass_tool(endpoint: str) -> str:
    """
    Query GMass API.
    
    Args:
        endpoint: API endpoint (campaigns, stats, etc.)
    
    Returns:
        JSON string with API results
    """
    # Execute GMass API call
    response = httpx.get(
        f"https://api.gmass.co/api/{endpoint}",
        headers={"Authorization": f"Bearer {self.gmass_api_key}"}
    )
    return response.text
```

---

### **Phase 2: Initialize ReAct Module** (15 minutes)

```python
# agents/strategy_agent.py - __init__

# Define available tools
self.tools = [
    audit_lead_flow_tool,
    query_supabase_tool,
    query_gmass_tool,
]

# Initialize ReAct module with tools
self.action_agent = dspy.ReAct(
    signature=StrategyConversation,
    tools=self.tools,
    max_iters=5  # Allow up to 5 tool calls
)

logger.info("   ReAct Module: ✅ Initialized with 3 tools")
logger.info("   Tools: audit_lead_flow, query_supabase, query_gmass")
```

---

### **Phase 3: Update Query Classification** (10 minutes)

```python
def _classify_query(self, message: str) -> str:
    """Classify query type for module selection.
    
    Returns:
        "simple" → dspy.Predict (fast, no reasoning)
        "action" → dspy.ReAct (tool calling)
        "complex" → dspy.ChainOfThought (reasoning, no tools)
    """
    message_lower = message.lower()
    
    # Action queries (need tools)
    action_keywords = [
        'audit', 'query', 'pull', 'get data', 'show me',
        'check gmass', 'check supabase', 'real data',
        'actual numbers', 'campaign stats'
    ]
    
    if any(keyword in message_lower for keyword in action_keywords):
        return "action"
    
    # Simple queries (no reasoning needed)
    if self._is_simple_query(message):
        return "simple"
    
    # Complex queries (reasoning but no tools)
    return "complex"
```

---

### **Phase 4: Route to ReAct** (10 minutes)

```python
# agents/strategy_agent.py - respond_to_message

# Classify query
query_type = self._classify_query(message)

if query_type == "simple":
    logger.info("📝 Simple query → Using Predict (fast)")
    result = self.simple_conversation(...)
    
elif query_type == "action":
    logger.info("🔧 Action query → Using ReAct (tool calling)")
    result = self.action_agent(
        context=system_context,
        user_message=message,
        conversation_history=history_text
    )
    
elif query_type == "complex":
    logger.info("🧠 Complex query → Using ChainOfThought (reasoning)")
    result = self.complex_conversation(...)
```

---

## **📊 Expected Behavior**

### **Before (ChainOfThought)**

```
User: "audit our lead flow"

ChainOfThought.forward (18s)
├─ Reasoning: "User wants audit. I should query GMass and Supabase..."
└─ Response: "Let me query GMass directly and get real metrics..."

[Pattern matching triggers]
audit_lead_flow() called manually
Returns: 0 campaigns, 0 emails (why?)

PROBLEM: ChainOfThought never called tools, just talked about them!
```

---

### **After (ReAct)**

```
User: "audit our lead flow"

ReAct.forward (20s)
├─ Thought: "User wants audit data. I have audit_lead_flow_tool."
├─ Action: audit_lead_flow_tool(timeframe_hours=24)
├─ Observation: {
│     "leads": {
│       "total": 15,
│       "by_tier": {"HOT": 3, "WARM": 7, "COOL": 5}
│     },
│     "emails": {
│       "sent": 42,
│       "delivered": 40,
│       "opened": 18,
│       "clicked": 5
│     }
│   }
├─ Thought: "I have real data. Format it nicely for Josh."
└─ Answer: "📊 Lead Flow Audit (Last 24h):
            
            **Leads Captured**: 15 total
            - 🔥 HOT: 3
            - 🌡️ WARM: 7
            - ❄️ COOL: 5
            
            **Email Performance**: 42 sent
            - ✅ Delivered: 40 (95.2%)
            - 📬 Opened: 18 (45.0%)
            - 🖱️ Clicked: 5 (12.5%)
            
            Data pulled from GMass & Supabase"

SUCCESS: Real data returned!
```

---

## **🎯 Key Differences**

| Feature | ChainOfThought | ReAct |
|---------|---------------|-------|
| **Reasoning** | ✅ Yes | ✅ Yes |
| **Tool Calling** | ❌ No | ✅ Yes |
| **Multi-step Actions** | ❌ No | ✅ Yes |
| **Observes Tool Results** | ❌ No | ✅ Yes |
| **Use Case** | Strategic thinking | Data retrieval & actions |
| **Speed** | Fast (no tools) | Slower (tool execution) |
| **Accuracy** | Can hallucinate | Real data only |

---

## **🚀 Implementation Steps**

### **1. Define Tools** (agents/strategy_agent.py)

```python
def _init_tools(self):
    """Initialize tools that ReAct can call."""
    
    def audit_lead_flow(timeframe_hours: int = 24) -> str:
        """Audit lead flow with real data."""
        import asyncio
        result = asyncio.run(
            self.audit_agent.audit_lead_flow(timeframe_hours)
        )
        return json.dumps(result, indent=2)
    
    def query_database(table: str, limit: int = 100) -> str:
        """Query Supabase database."""
        result = self.supabase.table(table).select("*").limit(limit).execute()
        return json.dumps(result.data, indent=2)
    
    def get_gmass_stats() -> str:
        """Get GMass campaign statistics."""
        # Call GMass API
        # Return JSON
        pass
    
    return [audit_lead_flow, query_database, get_gmass_stats]
```

### **2. Initialize ReAct** (__init__)

```python
# After Predict and ChainOfThought
self.tools = self._init_tools()
self.action_agent = dspy.ReAct(
    signature=StrategyConversation,
    tools=self.tools,
    max_iters=5
)
logger.info(f"   ReAct Module: ✅ Initialized with {len(self.tools)} tools")
```

### **3. Route Queries** (respond_to_message)

```python
query_type = self._classify_query(message)

if query_type == "action":
    logger.info("🔧 Using ReAct for tool calling")
    result = self.action_agent(...)
elif query_type == "simple":
    logger.info("📝 Using Predict for simple response")
    result = self.simple_conversation(...)
else:
    logger.info("🧠 Using ChainOfThought for reasoning")
    result = self.complex_conversation(...)
```

### **4. Test**

```
Slack: "audit our lead flow"

Expected:
├─ Log: "🔧 Using ReAct for tool calling"
├─ Log: "ReAct calling tool: audit_lead_flow"
├─ Log: "Tool returned: {15 leads, 42 emails...}"
└─ Response: Real data formatted nicely

Phoenix Trace:
ReAct.forward (20s)
├─ Thought span (2s)
├─ Tool call: audit_lead_flow (15s)
├─ Observation span (1s)
└─ Final answer (2s)
```

---

## **📋 File Changes Required**

### **agents/strategy_agent.py**

1. Add `_init_tools()` method
2. Initialize `self.action_agent = dspy.ReAct(...)`
3. Update `respond_to_message()` to route to ReAct
4. Add `_classify_query()` for 3-way routing

### **Testing**

1. Unit test tools individually
2. Test ReAct with mock tools
3. Integration test with real Supabase/GMass
4. Verify in Phoenix traces

---

## **⚠️ Important Notes**

### **Tool Function Signatures**

ReAct tools MUST:
- Be synchronous functions (use `asyncio.run()` for async)
- Return strings (JSON strings for complex data)
- Have clear docstrings (ReAct uses them to decide which tool to call)
- Handle errors gracefully

### **Tool Selection**

ReAct chooses tools based on:
- Function name
- Docstring description
- Parameter names and types
- User's query intent

Example:
```
User: "get gmass stats"

ReAct sees tools:
1. audit_lead_flow(timeframe_hours) - "Audit lead flow with real data"
2. query_database(table) - "Query Supabase database"
3. get_gmass_stats() - "Get GMass campaign statistics"

ReAct chooses: #3 get_gmass_stats() ← Most specific!
```

---

## **🎯 Success Metrics**

### **Verify ReAct is Working**

1. **Phoenix Traces**
   - Should see `ReAct.forward` spans
   - Should see tool call spans as children
   - Should see observation spans

2. **Railway Logs**
   ```
   🔧 Action query → Using ReAct (tool calling)
   ReAct calling tool: audit_lead_flow
   Tool returned: {...}
   ```

3. **Actual Data**
   - Audits return REAL numbers (not zeros)
   - Data matches GMass dashboard
   - Supabase data accurate

---

## **🚀 Deployment Plan**

### **Phase 1: Add ReAct (Today)**

1. ✅ Define tools
2. ✅ Initialize ReAct module
3. ✅ Update routing
4. ✅ Test locally
5. ✅ Deploy to Railway

### **Phase 2: Add More Tools (This Week)**

1. Close CRM tools
2. Slack message tools
3. Agent orchestration tools
4. Custom analytics tools

### **Phase 3: Multi-Step Actions (Next Week)**

Example:
```
User: "Get all HOT leads and email them"

ReAct:
├─ Thought: "Need to query HOT leads first"
├─ Action: query_database(table="leads", filter={"tier": "HOT"})
├─ Observation: [15 HOT leads]
├─ Thought: "Now draft emails for each"
├─ Action: draft_email_campaign(leads=[...], tier="HOT")
├─ Observation: "Campaign created: ID #123"
├─ Thought: "Send via GMass"
├─ Action: send_gmass_campaign(campaign_id=123)
└─ Answer: "✅ Sent 15 emails to HOT leads via campaign #123"
```

---

## **💡 Why This Fixes The Problem**

**Current**: "audit our lead flow"
- ChainOfThought TALKS about querying
- Hardcoded pattern matching detects "audit"
- Manual call to audit_agent
- Returns zeros (database error)

**With ReAct**: "audit our lead flow"
- ReAct ACTUALLY calls audit_lead_flow_tool
- Gets REAL data back
- Formats response with real numbers
- Returns accurate audit

**The difference**: ReAct can execute tools, ChainOfThought can only talk about them!

---

## **🎉 Expected Impact**

- ✅ Audits return real data (no more zeros)
- ✅ Can query multiple data sources intelligently
- ✅ Multi-step tool calling (query → analyze → act)
- ✅ No more hardcoded pattern matching
- ✅ LLM decides which tools to use
- ✅ Visible in Phoenix traces
- ✅ Extensible (add new tools easily)

---

**THIS IS THE MISSING PIECE!** 🚀

ReAct gives the Strategy Agent the ability to actually DO things, not just talk about doing things.
