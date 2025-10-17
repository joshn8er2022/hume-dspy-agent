# 🏗️ DSPy-First Architecture for Hume AI System

## **Philosophy: Zero Hardcoded Responses**

**RULE**: Every bot response, every analysis, every recommendation **MUST** go through a DSPy signature.

**Why?**
1. **Optimizable** - DSPy can auto-improve prompts via bootstrapping
2. **Consistent** - All responses follow same reasoning framework
3. **Traceable** - DSPy provides reasoning traces for debugging
4. **Maintainable** - Change behavior by modifying signatures, not scattered strings
5. **Quality** - LLM generates context-aware responses, not static templates

---

## **✅ Current State: Inbound Agent (CORRECT)**

### **Example: Proper DSPy Usage**
```python
# dspy_modules/signatures.py
class AnalyzeBusinessFit(dspy.Signature):
    """Analyze how well a B2B lead fits Hume Health's ICP."""
    
    company_context: str = dspy.InputField(desc="Hume Health context")
    business_size: str = dspy.InputField(desc="Business size")
    patient_volume: str = dspy.InputField(desc="Patient volume")
    
    fit_score: int = dspy.OutputField(desc="Business fit score (0-50)")
    reasoning: str = dspy.OutputField(desc="Explanation of fit")

# agents/inbound_agent.py
class InboundAgent(dspy.Module):
    def __init__(self):
        self.analyze_business = dspy.ChainOfThought(AnalyzeBusinessFit)
    
    def forward(self, lead_data):
        # DSPy generates response - NO hardcoded strings!
        result = self.analyze_business(
            company_context=get_context(),
            business_size=lead_data.business_size,
            patient_volume=lead_data.patient_volume
        )
        return result.fit_score, result.reasoning
```

**This is PERFECT** ✅

---

## **❌ Current Problem: Slack Bot & Strategy Agent**

### **Bad Example 1: Hardcoded Help**
```python
# api/slack_bot.py - WRONG! ❌
def get_help_message() -> str:
    return """🎯 Slack Agent Interface - Help
    
    **Call Agents:**
    • call research agent
    • call inbound agent
    ...
    """  # <- STATIC STRING!
```

**Why this is wrong:**
- Can't optimize this message for different users
- Can't adapt to system state
- Can't learn from user feedback
- Just a dumb template

### **Bad Example 2: Raw API Calls**
```python
# agents/strategy_agent.py - WRONG! ❌
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={"model": "claude-3.5-sonnet", ...}
    )
```

**Why this is wrong:**
- Bypasses DSPy entirely
- Can't use DSPy optimization
- No reasoning traces
- Not composable with other DSPy modules

---

## **✅ Correct Approach: Everything Through DSPy**

### **Good Example 1: Help Message**
```python
# dspy_modules/conversation_signatures.py
class GenerateHelpMessage(dspy.Signature):
    """Generate contextual help for user."""
    
    user_message: str = dspy.InputField()
    available_commands: str = dspy.InputField()
    user_history: str = dspy.InputField()
    
    help_message: str = dspy.OutputField()
    suggested_first_step: str = dspy.OutputField()

# api/slack_bot.py - CORRECT! ✅
help_module = dspy.ChainOfThought(GenerateHelpMessage)

def get_help_message(user_msg: str, history: str) -> str:
    result = help_module(
        user_message=user_msg,
        available_commands=get_commands(),
        user_history=history
    )
    return f"{result.help_message}\n\n**Try:** {result.suggested_first_step}"
```

### **Good Example 2: Pipeline Analysis**
```python
# dspy_modules/conversation_signatures.py
class PipelineAnalysis(dspy.Signature):
    """Analyze pipeline and generate insights."""
    
    pipeline_data: str = dspy.InputField()
    time_period: str = dspy.InputField()
    
    summary: str = dspy.OutputField()
    key_metrics: str = dspy.OutputField()
    insights: str = dspy.OutputField()

# agents/strategy_agent.py - CORRECT! ✅
class StrategyAgent(dspy.Module):
    def __init__(self):
        self.analyze_pipeline = dspy.ChainOfThought(PipelineAnalysis)
    
    async def show_pipeline_status(self):
        data = await self.fetch_pipeline_data()
        result = self.analyze_pipeline(
            pipeline_data=json.dumps(data),
            time_period="last 7 days"
        )
        return f"{result.summary}\n\n{result.key_metrics}\n\n{result.insights}"
```

---

## **🔧 Refactor Plan**

### **Phase 1: Strategy Agent** 🎯
**Files to update:**
- `agents/strategy_agent.py`
- Remove all hardcoded strings
- Replace with DSPy signatures from `dspy_modules/conversation_signatures.py`

**Signatures needed:**
- ✅ `StrategyConversation` (already created)
- ✅ `PipelineAnalysis` (already created)
- ✅ `GenerateRecommendations` (already created)

### **Phase 2: Slack Bot Interface** 💬
**Files to update:**
- `api/slack_bot.py`
- Replace every `def get_*_message()` with DSPy module

**Signatures needed:**
- ✅ `GenerateHelpMessage` (already created)
- ✅ `GenerateAgentMenu` (already created)
- ✅ `ListAgents` (already created)
- ✅ `QuickPipelineStatus` (already created)

### **Phase 3: Follow-Up Agent** 📧
**Files to update:**
- `agents/follow_up_agent.py`
- Add DSPy signatures for status messages

**Signatures needed:**
- ✅ `FollowUpStatus` (already created)

### **Phase 4: Research Agent** 🔍
**Files to update:**
- `agents/research_agent.py`
- Replace result formatting with DSPy

**Signatures needed:**
- `ResearchResultsFormatting`
- `ResearchRecommendations`

---

## **🚀 Benefits After Refactor**

### **1. Prompt Optimization**
```python
# Can run DSPy optimization later
from dspy.teleprompt import BootstrapFewShot

optimizer = BootstrapFewShot(metric=response_quality)
optimized_agent = optimizer.compile(
    strategy_agent,
    trainset=labeled_conversations
)
# Automatically finds better prompts!
```

### **2. Few-Shot Learning**
```python
# Add examples, DSPy learns patterns
examples = [
    dspy.Example(
        user_message="show me pipeline",
        response="Here's your pipeline: ...",
    ).with_inputs("user_message")
]

# DSPy uses these to improve responses
```

### **3. Consistency**
- All agents use same reasoning framework
- Responses have predictable structure
- Easy to A/B test different approaches

### **4. Debugging**
```python
# DSPy shows reasoning trace
dspy.inspect_history(n=1)
# See exactly why it generated that response!
```

---

## **📊 Architecture Diagram**

```
┌────────────── USER INPUT ──────────────┐
│  Slack message / API request           │
└────────────────┬───────────────────────┘
                 ↓
┌────────────── ROUTING ─────────────────┐
│  api/slack_bot.py                      │
│  - Pattern matching for commands       │
│  - Route to appropriate agent          │
└────────────────┬───────────────────────┘
                 ↓
┌────────── DSPY SIGNATURE ──────────────┐
│  dspy_modules/conversation_signatures  │
│  - Define inputs/outputs               │
│  - System prompt embedded              │
└────────────────┬───────────────────────┘
                 ↓
┌──────────── DSPY MODULE ───────────────┐
│  dspy.ChainOfThought / dspy.ReAct      │
│  - Reasoning + generation              │
│  - Uses Claude 3.5 Sonnet              │
│  - Structured Pydantic output          │
└────────────────┬───────────────────────┘
                 ↓
┌──────────── RESPONSE ──────────────────┐
│  Structured output (Pydantic model)    │
│  - response text                       │
│  - suggested_actions                   │
│  - confidence scores                   │
└────────────────┬───────────────────────┘
                 ↓
┌────────── FORMAT & SEND ───────────────┐
│  Slack formatting / API response       │
└────────────────────────────────────────┘
```

---

## **🎯 OpenRouter + DSPy Configuration**

### **Current Setup (Correct)**
```python
# core/dspy_setup.py
from dspy import LM

lm = LM(
    model="anthropic/claude-3.5-sonnet",  # OpenRouter model path
    api_key=settings.OPENROUTER_API_KEY,
    api_base="https://openrouter.ai/api/v1",
    max_tokens=1500,
    temperature=0.7
)

dspy.configure(lm=lm)
```

**This IS using DSPy properly!** ✅

The confusion: Using OpenRouter **through DSPy** is correct.  
The problem: Bypassing DSPy with raw `httpx` calls.

---

## **🔄 Migration Example: Help Message**

### **Before** ❌
```python
def get_help_message() -> str:
    return """🎯 Slack Agent Interface - Help
    
    **Call Agents:**
    • call research agent - Connect to Research Agent
    • call inbound agent - Connect to Inbound Agent
    
    **Quick Commands:**
    • pipeline status - Show current pipeline
    
    Try any command to get started!
    """
```

### **After** ✅
```python
# In __init__
self.help_generator = dspy.ChainOfThought(GenerateHelpMessage)

# In function
def get_help_message(user_msg: str, history: List[str]) -> str:
    result = self.help_generator(
        user_message=user_msg,
        available_agents="Research, Inbound, Follow-Up, Strategy",
        user_history="\n".join(history[-5:])
    )
    
    response = result.help_message
    if result.suggested_first_step:
        response += f"\n\n💡 **Try this first:** {result.suggested_first_step}"
    
    return response
```

**Benefits:**
- Adapts to what user just asked
- Considers user's history
- Suggests most relevant command
- Can be optimized by DSPy later
- LLM generates natural language

---

## **📝 Implementation Checklist**

### **Strategy Agent**
- [ ] Replace `_llm_chat()` with DSPy `StrategyConversation`
- [ ] Replace pipeline formatting with DSPy `PipelineAnalysis`
- [ ] Replace recommendations with DSPy `GenerateRecommendations`
- [ ] Remove all `return "static string"` statements

### **Slack Bot**
- [ ] Replace `get_help_message()` with `GenerateHelpMessage`
- [ ] Replace `get_available_agents()` with `ListAgents`
- [ ] Replace agent menus with `GenerateAgentMenu`
- [ ] Replace pipeline status with `QuickPipelineStatus`

### **Follow-Up Agent**
- [ ] Add `FollowUpStatus` signature
- [ ] Replace status formatting with DSPy
- [ ] Use DSPy for email template selection reasoning

### **Research Agent**
- [ ] Create `ResearchResultsFormatting` signature
- [ ] Replace result formatting with DSPy
- [ ] Add `ResearchRecommendations` for next steps

---

## **🎓 DSPy Best Practices**

### **1. Descriptive Field Descriptions**
```python
# Good ✅
user_message: str = dspy.InputField(
    desc="User's natural language question about pipeline (e.g., 'how many HOT leads?')"
)

# Bad ❌
user_message: str = dspy.InputField(desc="message")
```

### **2. System Context in Signature Docstring**
```python
class MySignature(dspy.Signature):
    """You are an expert in X. Do Y. Consider Z.
    
    Important: Always check A before suggesting B.
    Never recommend C unless D is present.
    """
```

### **3. Structured Outputs**
```python
# Good ✅ - Multiple fields
summary: str = dspy.OutputField()
confidence: int = dspy.OutputField()
next_steps: str = dspy.OutputField()

# Less ideal - Single blob
response: str = dspy.OutputField()  # Everything in one string
```

### **4. Composition**
```python
# Chain multiple DSPy modules
class ComplexAgent(dspy.Module):
    def __init__(self):
        self.analyze = dspy.ChainOfThought(Analyze)
        self.recommend = dspy.ChainOfThought(Recommend)
    
    def forward(self, input):
        analysis = self.analyze(input=input)
        recs = self.recommend(analysis=analysis.result)
        return recs
```

---

## **🚀 Future: LangGraph Integration**

Once all agents are pure DSPy, we can add LangGraph for:

```python
from langgraph.graph import StateGraph

# Define multi-agent workflow
workflow = StateGraph(state_schema=AgentState)

workflow.add_node("qualify", inbound_agent)
workflow.add_node("research", research_agent)
workflow.add_node("follow_up", follow_up_agent)

# Add conditional routing
workflow.add_conditional_edges(
    "qualify",
    lambda state: "research" if state.score > 70 else "follow_up"
)

# Compile and run
app = workflow.compile()
result = app.invoke({"lead": lead_data})
```

But we need pure DSPy modules first!

---

## **📚 Summary**

### **Core Principle**
**EVERYTHING goes through DSPy signatures. NO exceptions.**

### **What This Means**
- ❌ No `return "static string"`
- ❌ No raw OpenRouter API calls
- ❌ No hardcoded templates
- ✅ Every response = DSPy module execution
- ✅ Every analysis = DSPy signature
- ✅ Every formatting = DSPy-generated

### **Why This Matters**
You're building a **truly agentic system** where:
- LLM reasons through every response
- Behavior is optimizable via DSPy
- Quality improves with more examples
- System is maintainable and composable

This is the difference between:
- ❌ **A bot with AI features** (what most people build)
- ✅ **An AI-native agentic system** (what you're building)

---

**Next Step**: Refactor Strategy Agent to use DSPy signatures exclusively! 🚀
