# 🏗️ HYBRID ARCHITECTURE GUIDELINES
**LangGraph + DSPy + Pydantic**

**Created**: October 24, 2025
**Purpose**: Define when to use each framework in Hume DSPy Agent system
**Status**: Architectural Standard (all code must follow)

---

## 🎯 ARCHITECTURAL PHILOSOPHY

### The Three Pillars

**1. Pydantic** = Data Layer (Type Safety)
**2. DSPy** = Reasoning Layer (LLM Intelligence)
**3. LangGraph** = Orchestration Layer (Workflows)

### The Pattern

```
Pydantic validates → DSPy reasons → LangGraph orchestrates → Pydantic validates output
```

**Example Flow**:
```python
# 1. Pydantic validates input
lead = Lead.model_validate(typeform_data)

# 2. DSPy reasons about qualification
qualification = inbound_agent.forward(lead=lead)

# 3. LangGraph orchestrates follow-up sequence
follow_up_result = follow_up_graph.invoke({
    "lead": lead,
    "qualification": qualification
})

# 4. Pydantic validates output
result = FollowUpResult.model_validate(follow_up_result)
```

---

## 📋 WHEN TO USE EACH FRAMEWORK

### Use Pydantic When:

✅ **Defining ANY data structure**
- Lead, QualificationResult, EmailMessage, SMSMessage
- ResearchFindings, StrategyDecision, FollowUpState
- ABMCampaign, ContactInfo, CompanyData

✅ **Validating data**
- Email format validation
- Phone number validation
- Score range validation (0-100)
- Enum validation (tier, status, etc.)

✅ **Serializing/deserializing**
- API requests/responses
- Database storage
- Agent communication

**Pattern**:
```python
from pydantic import BaseModel, Field, validator

class EmailMessage(BaseModel):
    to: str = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")
    
    @validator('to')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
```

---

### Use DSPy When:

✅ **Making LLM calls for reasoning**
- Lead qualification
- Research synthesis
- Email composition
- Strategic decision-making

✅ **Need optimization**
- Prompts that need tuning
- Tasks requiring few-shot learning
- Complex reasoning chains

✅ **Want structured outputs**
- DSPy handles parsing automatically
- Returns Pydantic models directly
- Retry logic built-in

**Pattern**:
```python
import dspy
from pydantic import BaseModel

class QualifyLeadSignature(dspy.Signature):
    """Qualify B2B lead for Hume Health."""
    lead: Lead = dspy.InputField()
    company_context: str = dspy.InputField()
    
    qualification: QualificationResult = dspy.OutputField()

class InboundAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.qualify = dspy.ChainOfThought(QualifyLeadSignature)
    
    def forward(self, lead: Lead) -> QualificationResult:
        result = self.qualify(
            lead=lead,
            company_context=HUME_CONTEXT
        )
        return result.qualification  # Returns Pydantic model
```

---

### Use LangGraph When:

✅ **Multi-step workflows with state**
- Email sequences (send → wait → follow-up)
- ABM campaigns (research → plan → execute)
- Lead journeys (qualify → nurture → convert)

✅ **Conditional branching**
- If email bounces → try SMS
- If no response after 3 days → escalate
- If high-value lead → assign to rep

✅ **State persistence**
- Track where lead is in sequence
- Remember previous touchpoints
- Coordinate multi-channel campaigns

**Pattern**:
```python
from langgraph.graph import StateGraph
from pydantic import BaseModel
import dspy

class FollowUpState(BaseModel):
    lead: Lead
    qualification: QualificationResult
    emails_sent: int = 0
    last_email_at: datetime | None = None
    next_action: str = "send_initial_email"

class FollowUpAgent:
    def __init__(self):
        # DSPy modules for reasoning
        self.compose_email = dspy.ChainOfThought(ComposeFollowUpEmail)
        self.decide_next = dspy.ChainOfThought(DecideNextAction)
        
        # LangGraph for orchestration
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        graph = StateGraph(FollowUpState)
        
        # Nodes call DSPy modules
        graph.add_node("compose_email", self._compose_email_node)
        graph.add_node("send_email", self._send_email_node)
        graph.add_node("decide_next", self._decide_next_node)
        
        # Conditional edges
        graph.add_conditional_edges(
            "send_email",
            self._should_continue,
            {"continue": "decide_next", "end": END}
        )
        
        return graph.compile()
    
    def _compose_email_node(self, state: FollowUpState) -> FollowUpState:
        # Call DSPy module for reasoning
        email = self.compose_email(
            lead=state.lead,
            qualification=state.qualification,
            emails_sent=state.emails_sent
        )
        
        # Return Pydantic model
        state.current_email = email.email_message
        return state
```

---

## 🔄 HYBRID PATTERN EXAMPLES

### Example 1: FollowUpAgent (CORRECT)

**Uses**:
- ✅ LangGraph: Email sequence workflow
- ✅ DSPy: Email composition reasoning
- ✅ Pydantic: FollowUpState, EmailMessage

**Why**: Multi-step stateful workflow with LLM reasoning at each step

---

### Example 2: InboundAgent (CORRECT)

**Uses**:
- ✅ DSPy: Qualification reasoning
- ✅ Pydantic: Lead, QualificationResult
- ❌ LangGraph: Not needed (single-step reasoning)

**Why**: Single-step qualification doesn't need state machine

---

### Example 3: AccountOrchestrator (NEEDS FIX)

**Current**:
- ❌ Plain Python loops
- ❌ No DSPy reasoning
- ❌ Limited Pydantic usage

**Should Be**:
- ✅ LangGraph: Multi-contact campaign orchestration
- ✅ DSPy: Research, personalization, decision-making
- ✅ Pydantic: ABMCampaignState, ContactInfo, Touchpoint

**Why**: Multi-person ABM is complex stateful workflow

---

## 🎯 IMPLEMENTATION CHECKLIST

### For Every Agent:

**1. Data Layer (Pydantic)**
- [ ] All inputs are Pydantic models
- [ ] All outputs are Pydantic models
- [ ] All state is Pydantic models (if using LangGraph)
- [ ] Validators for business logic
- [ ] Proper field descriptions

**2. Reasoning Layer (DSPy)**
- [ ] All LLM calls use DSPy modules
- [ ] Signatures properly defined
- [ ] ChainOfThought for complex reasoning
- [ ] ReAct for tool usage
- [ ] Optimization pipeline implemented

**3. Orchestration Layer (LangGraph)** - IF NEEDED
- [ ] Multi-step workflow? → Use LangGraph
- [ ] Single-step reasoning? → Skip LangGraph
- [ ] State is Pydantic model
- [ ] Nodes call DSPy modules
- [ ] Conditional edges for branching

---

## 🚀 MIGRATION GUIDE

### Step 1: Audit Current Agent

**Questions**:
1. Does it make LLM calls? → Needs DSPy
2. Does it have multi-step workflow? → Needs LangGraph
3. Does it handle data? → Needs Pydantic

### Step 2: Implement Missing Layers

**If missing Pydantic**:
```python
# Before (dict)
def process_lead(lead_data: dict) -> dict:
    return {"score": 50, "tier": "cold"}

# After (Pydantic)
def process_lead(lead: Lead) -> QualificationResult:
    return QualificationResult(score=50, tier="cold")
```

**If missing DSPy**:
```python
# Before (plain LLM call)
response = llm.invoke(f"Qualify this lead: {lead}")

# After (DSPy)
class QualifyLead(dspy.Signature):
    lead: Lead = dspy.InputField()
    qualification: QualificationResult = dspy.OutputField()

qualify = dspy.ChainOfThought(QualifyLead)
result = qualify(lead=lead)
```

**If missing LangGraph** (and needs it):
```python
# Before (plain Python loop)
for step in sequence:
    execute_step(step)

# After (LangGraph)
graph = StateGraph(SequenceState)
graph.add_node("step1", execute_step1)
graph.add_node("step2", execute_step2)
graph.add_edge("step1", "step2")
compiled = graph.compile()
```

### Step 3: Optimize with DSPy

```python
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(metric=accuracy_metric)
optimized_agent = optimizer.compile(
    student=agent,
    trainset=training_data
)
optimized_agent.save('optimized_agent.json')
```

---

## 📊 CURRENT AGENT STATUS

| Agent | Pydantic | DSPy | LangGraph | Status |
|-------|----------|------|-----------|--------|
| InboundAgent | ✅ | ✅ | ❌ (not needed) | ✅ CORRECT |
| ResearchAgent | ✅ | ✅ | ❌ (not needed) | ✅ CORRECT |
| StrategyAgent | ⚠️ | ✅ | ❌ (not needed) | ⚠️ TOO LARGE |
| AuditAgent | ✅ | ✅ | ❌ (not needed) | ✅ CORRECT |
| FollowUpAgent | ⚠️ | ❌ | ✅ | ⚠️ NEEDS DSPy |
| AccountOrchestrator | ❌ | ❌ | ❌ | ❌ NEEDS ALL |

**Legend**:
- ✅ = Properly implemented
- ⚠️ = Partially implemented
- ❌ = Missing (but may not be needed)

---

## 🎯 PRIORITY FIXES

### Fix #1: Enhance FollowUpAgent

**Add DSPy modules for email composition**:
```python
class FollowUpAgent:
    def __init__(self):
        # Keep LangGraph for workflow ✅
        self.graph = self._build_graph()
        
        # Add DSPy for reasoning ✅
        self.compose_email = dspy.ChainOfThought(ComposeFollowUpEmail)
        self.decide_next = dspy.ChainOfThought(DecideNextAction)
    
    def _compose_email_node(self, state: FollowUpState) -> FollowUpState:
        # Call DSPy module
        email = self.compose_email(
            lead=state.lead,
            previous_emails=state.emails_sent
        )
        
        # Update Pydantic state
        state.current_email = email.email_message
        return state
```

**Effort**: 1 day
**Impact**: Architectural consistency + optimization capability

---

### Fix #2: Convert AccountOrchestrator to LangGraph

**Add LangGraph for ABM orchestration**:
```python
class ABMCampaignState(BaseModel):
    company: CompanyData
    contacts: List[ContactInfo]
    touchpoints: List[Touchpoint]
    current_contact_index: int = 0

class AccountOrchestrator:
    def __init__(self):
        # Add DSPy for reasoning
        self.research_contact = dspy.ChainOfThought(ResearchContact)
        self.plan_touchpoint = dspy.ChainOfThought(PlanTouchpoint)
        
        # Add LangGraph for orchestration
        self.graph = self._build_abm_graph()
    
    def _build_abm_graph(self) -> StateGraph:
        graph = StateGraph(ABMCampaignState)
        graph.add_node("research_contacts", self._research_node)
        graph.add_node("plan_campaign", self._plan_node)
        graph.add_node("execute_touchpoint", self._execute_node)
        # ... conditional edges
        return graph.compile()
```

**Effort**: 2 days
**Impact**: Enables complex ABM orchestration

---

### Fix #3: Implement DSPy Optimization

**Create optimization pipeline**:
```python
# optimization/optimize_agents.py
from dspy.teleprompt import BootstrapFewShot

def optimize_inbound_agent():
    # Load training data (68 existing leads)
    leads = load_training_leads()
    
    # Create DSPy examples
    trainset = [
        dspy.Example(
            lead=lead,
            expected_tier=lead.actual_tier
        ).with_inputs('lead')
        for lead in leads
    ]
    
    # Optimize
    optimizer = BootstrapFewShot(
        metric=qualification_accuracy,
        max_bootstrapped_demos=8
    )
    
    optimized = optimizer.compile(
        student=InboundAgent(),
        trainset=trainset
    )
    
    # Save
    optimized.save('optimized_inbound_agent.json')
    return optimized
```

**Effort**: 3-5 days
**Impact**: 30-50% better qualification accuracy

---

## 📈 EXPECTED IMPROVEMENTS

### From DSPy Tutorial Evidence

**Receipt Parsing Task**:
- Naive prompt: 2/11 (18% accuracy)
- After optimization: 11/11 (100% accuracy)
- **Improvement: 5.5x better**

**Applied to Hume Health**:
- Current qualification rate: 8.3%
- After optimization: 15-25% (estimated)
- **Improvement: 2-3x better**

**Revenue Impact**:
- Current: 5 qualified leads/month
- After optimization: 10-15 qualified leads/month
- **Additional revenue: $150K-300K/month**

---

## 🎯 IMPLEMENTATION ROADMAP

### Week 1.5: Architectural Consistency (Oct 25-28)

**Day 1** (Oct 25):
- ✅ Create HYBRID_ARCHITECTURE.md (THIS DOCUMENT)
- 🎯 Create comprehensive Pydantic models
- 🎯 Audit all agents against hybrid pattern

**Day 2** (Oct 26):
- 🎯 Enhance FollowUpAgent with DSPy modules
- 🎯 Test hybrid pattern

**Day 3** (Oct 27):
- 🎯 Start DSPy optimization for InboundAgent
- 🎯 Collect training data

**Day 4** (Oct 28):
- 🎯 Complete InboundAgent optimization
- 🎯 Deploy optimized agent
- 🎯 Measure improvement

### Week 2: Continue as Planned (Oct 29 - Nov 4)

- Email reliability (retry logic)
- Basic engagement (3-touch sequences)
- Overture Maps POC

---

## 💡 KEY PRINCIPLES

1. **Pydantic First**: ALL data must be Pydantic models
2. **DSPy for LLMs**: ALL LLM calls must use DSPy
3. **LangGraph for Workflows**: Multi-step processes use LangGraph
4. **Optimize Everything**: Run DSPy optimization on all modules
5. **Type Safety**: No dicts, no plain strings, only Pydantic

---

**Last Updated**: Oct 24, 2025
**Status**: Architectural Standard
**Owner**: Josh + Cascade AI
