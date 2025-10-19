# 🔧 Phase 0.3: Agent Architecture Refactoring

**Start Date**: October 19, 2025, 3:04 PM PST  
**Timeline**: 5-7 hours  
**Status**: 🟢 IN PROGRESS

---

## **📋 Overview**

Converting agents to proper `dspy.Module` architecture for:
- ✅ Consistent patterns across agents
- ✅ DSPy optimization/compilation
- ✅ Better testability
- ✅ Cleaner code structure
- ✅ Easier maintenance

---

## **🎯 Tasks**

### **Task 1: Refactor StrategyAgent** ⏰ 2 hours
**Status**: 🟡 Starting  
**File**: `agents/strategy_agent.py`

**Current State**:
- Mixed architecture (some DSPy, some custom methods)
- Direct method calls for different conversation types
- Not using dspy.Module inheritance

**Target State**:
```python
class StrategyAgent(dspy.Module):
    """Strategy Agent as proper DSPy Module"""
    
    def __init__(self):
        super().__init__()
        
        # Sub-agents
        self.inbound = InboundAgent()
        self.research = ResearchAgent()
        self.follow_up = FollowUpAgent()
        
        # DSPy modules
        self.simple_conversation = dspy.Predict(StrategyConversation)
        self.complex_conversation = dspy.ChainOfThought(StrategyConversation)
        self.react_agent = dspy.ReAct(
            signature=StrategyConversation,
            tools=self._init_tools()
        )
    
    def forward(self, message: str, context: dict = None) -> str:
        """Main forward pass - classify and route"""
        
        # Classify query
        query_type = self._classify_query(message)
        
        # Route to appropriate module
        if query_type == "simple":
            return self.simple_conversation(
                user_message=message,
                context=context
            ).response
        
        elif query_type == "complex":
            return self.complex_conversation(
                user_message=message,
                context=context
            ).response
        
        else:  # action
            return self.react_agent(
                user_message=message,
                context=context
            ).response
```

**Steps**:
1. Add `dspy.Module` inheritance
2. Convert conversation methods to DSPy modules
3. Implement `forward()` method
4. Keep ReAct tools as-is (already good)
5. Test with existing Slack integration

---

### **Task 2: Refactor ResearchAgent** ⏰ 3 hours
**Status**: 🔴 Not Started  
**File**: `agents/research_agent.py`

**Current State**:
- Custom class with async methods
- Direct LLM calls via Perplexity
- No DSPy integration

**Target State**:
```python
class ResearchAgent(dspy.Module):
    """Research Agent as DSPy Module with MCP tools"""
    
    def __init__(self):
        super().__init__()
        
        # Research planning
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        
        # ReAct for tool use
        self.research_executor = dspy.ReAct(
            signature=ExecuteResearch,
            tools=[
                self.perplexity_search,
                self.scrape_website,
                self.analyze_company
            ]
        )
        
        # Synthesis
        self.synthesize = dspy.ChainOfThought(SynthesizeResearch)
    
    def forward(self, query: str, lead_context: dict = None) -> dict:
        """Research workflow"""
        
        # 1. Plan research
        plan = self.plan_research(
            query=query,
            lead_context=lead_context
        )
        
        # 2. Execute research
        findings = self.research_executor(
            plan=plan.research_plan,
            query=query
        )
        
        # 3. Synthesize results
        synthesis = self.synthesize(
            findings=findings.result,
            original_query=query
        )
        
        return {
            "plan": plan.research_plan,
            "findings": findings.result,
            "synthesis": synthesis.summary
        }
```

**Steps**:
1. Create DSPy signatures for research workflow
2. Convert to `dspy.Module`
3. Implement multi-step research pipeline
4. Integrate MCP Perplexity tool
5. Test with sample company research

---

### **Task 3: Refactor AuditAgent** ⏰ 2 hours
**Status**: 🔴 Not Started  
**File**: `agents/audit_agent.py`

**Decision Point**: Should AuditAgent be a DSPy Module?

**Option A: Keep as Service** (Recommended)
- AuditAgent is primarily data aggregation
- No reasoning required
- Direct Supabase queries
- Simple metrics calculation

**Option B: Convert to DSPy Module**
- Add reasoning about metrics
- Generate insights automatically
- Recommend actions based on data

**Recommendation**: 
- Keep AuditAgent as a service (data layer)
- Add separate `AuditAnalyzer` DSPy module if insights needed

**If converting**:
```python
class AuditAnalyzer(dspy.Module):
    """Analyze audit data and generate insights"""
    
    def __init__(self):
        super().__init__()
        self.analyzer = dspy.ChainOfThought(AuditAnalysis)
    
    def forward(self, metrics: dict) -> dict:
        """Analyze metrics and generate insights"""
        
        analysis = self.analyzer(
            metrics=metrics,
            time_period="7 days"
        )
        
        return {
            "insights": analysis.insights,
            "recommendations": analysis.recommendations,
            "concerns": analysis.concerns
        }
```

**Steps**:
1. Decide: Service vs DSPy Module
2. If DSPy: Create signatures
3. If DSPy: Implement analyzer
4. Test with current audit data

---

## **🧪 Testing Plan**

### **Test 1: StrategyAgent**
```bash
# Test simple query
curl -X POST http://localhost:8000/a2a/introspect \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the status of the pipeline?"}'

# Test complex query
curl -X POST http://localhost:8000/a2a/introspect \
  -H "Content-Type: application/json" \
  -d '{"query": "analyze our conversion rates and suggest improvements"}'

# Test action query
curl -X POST http://localhost:8000/a2a/introspect \
  -H "Content-Type: application/json" \
  -d '{"query": "audit our lead flow for the past 24 hours"}'
```

### **Test 2: ResearchAgent**
```python
# Test research workflow
agent = ResearchAgent()
result = agent(
    query="Research Acme Healthcare - company info, tech stack, decision makers",
    lead_context={"company": "Acme Healthcare", "industry": "healthcare"}
)

assert "plan" in result
assert "findings" in result
assert "synthesis" in result
```

### **Test 3: Integration**
```python
# Test StrategyAgent calling ResearchAgent
strategy = StrategyAgent()
response = strategy(
    message="Research the top 3 HOT leads and tell me which to prioritize",
    context={"mode": "action"}
)

# Should use ReAct to:
# 1. Query HOT leads from audit agent
# 2. Call research agent for each
# 3. Synthesize recommendations
```

---

## **📊 Success Criteria**

### **Code Quality**
- ✅ All agents inherit from `dspy.Module`
- ✅ Use `forward()` method consistently
- ✅ DSPy signatures defined clearly
- ✅ No breaking changes to external APIs

### **Functionality**
- ✅ All existing features still work
- ✅ Slack integration unaffected
- ✅ Webhook processing unaffected
- ✅ Phoenix tracing working

### **Performance**
- ✅ No significant latency increase
- ✅ Token usage similar or better
- ✅ All tests passing

---

## **🚀 Deployment Plan**

### **Step 1: Local Testing** ⏰ 30 min
1. Run full test suite
2. Test each agent individually
3. Test integration flows
4. Check Phoenix traces

### **Step 2: Staging** ⏰ 15 min
1. Deploy to Railway staging (if available)
2. Smoke test with real Slack
3. Monitor logs for 15 minutes

### **Step 3: Production** ⏰ 15 min
1. Deploy to Railway production
2. Monitor startup logs
3. Test with real Slack message
4. Watch Phoenix dashboard

---

## **⏱️ Timeline**

**Day 1 (Today)**:
- 3:00 PM - 5:00 PM: StrategyAgent refactor (2 hours)
- 5:00 PM - 5:30 PM: Test StrategyAgent (30 min)

**Day 2 (Tomorrow)**:
- Morning: ResearchAgent refactor (3 hours)
- Afternoon: Test ResearchAgent (30 min)

**Day 3**:
- Morning: AuditAgent decision + implementation (2 hours)
- Afternoon: Integration testing + deployment (1 hour)

**Total**: 5-7 hours over 2-3 days

---

## **🎯 Current Status**

**Started**: October 19, 2025, 3:04 PM PST  
**Current Task**: StrategyAgent refactoring  
**Next**: Start implementing `dspy.Module` inheritance

---

**Ready to start StrategyAgent refactoring?** Let's do it! 🚀
