# 🗺️ Development Roadmap - Hume DSPy Agent System

**Last Updated**: October 18, 2025  
**Status**: DSPy Core Operational ✅ | Agent Zero Audit Complete ✅ | Ready for MCP Integration

---

## **📊 Current State Analysis**

### **What We Have** ✅

**Core Infrastructure**:
- ✅ DSPy ChainOfThought modules (all agents)
- ✅ Claude 3.5 Sonnet via OpenRouter configured globally
- ✅ 100% DSPy conversational layer (no hardcoded responses)
- ✅ 4 specialized agents (Inbound, Research, Follow-Up, Strategy)
- ✅ Slack integration with conversational AI
- ✅ Supabase database for lead storage
- ✅ GMass email automation
- ✅ Typeform/VAPI webhook processing

**Recent Achievements** (Oct 18, 2025):
- ✅ Fixed DSPy configuration errors (LM not loaded)
- ✅ Fixed OpenRouter API integration (405 error resolved)
- ✅ Fixed AttributeError with optional output fields
- ✅ Agent Zero framework audit (5000+ lines of code reviewed)
- ✅ Identified production-ready MCP client implementation
- ✅ Documented integration strategy for FAISS memory + instruments

### **Critical Gaps** ❌

**Data Loss Issues**:
- ❌ Follow-up state persistence (using in-memory only)
- ❌ Research Agent API keys (Clearbit, Apollo, Perplexity)
- ❌ Real Supabase queries (showing mock data)
- ❌ Close CRM integration (stub only)

**Advanced Features**:
- ❌ MCP (Model Context Protocol) integration (100+ instant integrations!)
- ❌ Vector DB memory (FAISS for semantic search)
- ❌ Instrument system (unlimited tools without prompt bloat)
- ❌ DSPy ReAct agents (tool-using agents)
- ❌ DSPy optimization/training pipeline
- ❌ Autonomous multi-agent collaboration
- ❌ Cost optimization (free models for background work)
- ❌ Asynchronous agent-to-agent workflows
- ❌ Background research/strategizing loops
- ❌ Zapier MCP integration
- ❌ LangGraph workflow orchestration

---

## **🔴 Phase 0: Critical Bug Fixes (DO THIS FIRST!)**
**Timeline**: 2-3 days  
**Priority**: CRITICAL - Blocks everything else  
**Status**: 🔴 NOT STARTED

See `docs/PHASE_0_CRITICAL_FIXES.md` for detailed implementation.

### **Why Phase 0 Exists**:
Currently losing data and showing fake numbers. Must fix before adding new features.

### **Tasks**:
1. ✅ **PostgreSQL Checkpointer** (30 min) - Stop losing follow-up state on restart
2. ✅ **Research Agent API Keys** (5 min) - Add Clearbit, Apollo, Perplexity keys to Railway
3. ✅ **Real Supabase Queries** (2 hours) - Replace mock data with actual queries
4. ✅ **Close CRM Integration** (3 hours) - Full two-way sync implementation
5. ✅ **LinkedIn & Company Intel** (4 hours) - Real research capability

### **Impact**:
- **Before**: 37/63 tools operational (59%)
- **After**: 50/63 tools operational (79%)
- **Gain**: +20% operational, no data loss, real insights

---

## **🚀 Phase 0.5: Agent Zero Integration (NEW!)**
**Timeline**: 1-2 weeks  
**Priority**: HIGH - Unlocks massive capability  
**Status**: 🟡 PLANNED

Based on deep code audit of Agent Zero framework (5000+ lines reviewed).

### **Goal**:
Integrate production-ready components from Agent Zero for instant capability boost.

### **Tasks**:

#### **0.5.1 MCP Client Integration** (2-3 days) ⭐⭐⭐⭐⭐
**Value**: 100+ instant integrations (GitHub, Slack, Calendar, Drive, etc.)

```python
# core/mcp_client.py
from mcp import ClientSession, stdio_client
from python.helpers.mcp_handler import MCPConfig  # From Agent Zero

class HumeMCPIntegration:
    """Port Agent Zero's MCP client"""
    def __init__(self):
        self.config = MCPConfig.get_instance()
    
    async def initialize(self):
        # Connect to MCP servers from settings
        await self.config.update(settings["mcp_servers"])
    
    def get_tools_for_agent(self, agent_type: str):
        # Inject MCP tools into DSPy ReAct agents
        return self.config.get_tools_prompt()
```

**Enables**:
- GitHub integration (repos, issues, PRs)
- Slack (messaging, channels)
- Google Calendar, Drive, Gmail
- PostgreSQL queries
- Brave Search
- 100+ more from MCP server ecosystem

#### **0.5.2 FAISS Vector Memory** (1-2 days) ⭐⭐⭐⭐⭐
**Value**: Semantic memory + learning from past solutions

```python
# memory/vector_memory.py
from langchain_community.vectorstores import FAISS
import faiss

class HumeMemory:
    """Port Agent Zero's FAISS memory"""
    def __init__(self):
        index = faiss.IndexFlatIP(embedding_dim)
        self.db = FAISS(
            embedding_function=embedder,
            index=index,
            docstore=InMemoryDocstore()
        )
    
    async def remember_solution(self, problem: str, solution: str):
        self.db.add_documents([
            Document(page_content=f"{problem} → {solution}",
                    metadata={"type": "solution"})
        ])
    
    async def recall_similar(self, problem: str):
        return self.db.similarity_search(problem, k=3)
```

**Enables**:
- Agents learn from every interaction
- Semantic search for past solutions
- Auto-improving over time

#### **0.5.3 Instrument System** (2-3 days) ⭐⭐⭐⭐
**Value**: Unlimited tools without prompt bloat

```python
# instruments/instrument_manager.py
class InstrumentManager:
    """Store tool descriptions in vector DB, not system prompt"""
    def __init__(self):
        self.vector_db = FAISS(...)
    
    def register_instrument(self, name: str, description: str, script_path: str):
        """Add instrument to vector DB"""
        self.vector_db.add_documents([
            Document(page_content=description,
                    metadata={"name": name, "path": script_path, "type": "instrument"})
        ])
    
    async def recall_relevant_instruments(self, query: str, k=3):
        """Semantic search for relevant tools"""
        return self.vector_db.similarity_search(query, k=k)
```

**Enables**:
- Add new tools without redeploying
- No system prompt token bloat
- Semantic tool discovery

### **Total Impact**:
- **MCP**: 100+ integrations in 2-3 days (vs months to build manually)
- **Memory**: Agents get smarter over time
- **Instruments**: Unlimited extensibility

---

## **🎯 Phase 1: DSPy ReAct Agents & Tool Use**
**Timeline**: Week 3-4  
**Priority**: HIGH  
**Status**: 🟡 PLANNED (After Phase 0 + 0.5)

### **Goal**: 
Transform agents from pure conversation to tool-using ReAct agents that can:
- Query databases dynamically
- Call external APIs
- Execute multi-step reasoning with tools

### **Implementation**:

#### **1.1 Convert Strategy Agent to ReAct**
```python
# agents/strategy_agent.py
from dspy import ReAct

class StrategyAgentTools:
    """Tools available to Strategy Agent"""
    
    @tool
    def query_pipeline_stats(self, days: int = 7) -> Dict:
        """Get actual pipeline statistics from Supabase"""
        # Query real data instead of placeholders
        
    @tool
    def get_agent_status(self, agent_name: str) -> Dict:
        """Check health and recent activity of specific agent"""
        
    @tool
    def analyze_lead_tier_distribution(self) -> Dict:
        """Get current lead distribution across tiers"""
        
    @tool
    def search_leads(self, criteria: Dict) -> List[Lead]:
        """Search leads by various criteria"""

# Convert to ReAct
self.strategy_react = dspy.ReAct(
    signature=StrategyConversation,
    tools=[
        query_pipeline_stats,
        get_agent_status,
        analyze_lead_tier_distribution,
        search_leads
    ]
)
```

#### **1.2 Convert Research Agent to ReAct**
- Add Clearbit API tool
- Add Apollo API tool  
- Add Perplexity search tool
- Add LinkedIn scraping tool
- Add company website analyzer

#### **1.3 Benefits**:
- Agents can answer questions with REAL data
- Multi-step reasoning ("Let me check the database... Now let me analyze...")
- More reliable than pure generation

---

## **🎯 Phase 1.5: Agent Delegation & Communication (NEW!)**
**Timeline**: 3-4 days  
**Priority**: MEDIUM-HIGH  
**Status**: 🟡 PLANNED

**See**: `docs/AGENT_DELEGATION_ANALYSIS.md` for detailed analysis

### **Goal**:
Enable agents to delegate complex tasks to subordinate agents and communicate with each other.

**Based on Agent Zero's `call_subordinate` pattern - analyzed from source code!**

### **Implementation**:

#### **1.5.1 Add Delegation Infrastructure** (1 day)
```python
# core/agent_delegation.py
class AgentDelegation:
    """Enable agents to create specialized subordinates"""
    
    def __init__(self, agent):
        self.agent = agent
        self.subordinates: Dict[str, Agent] = {}
    
    async def call_subordinate(
        self,
        profile: str,  # "competitor_analyst", "market_researcher"
        message: str,
        reset: bool = False
    ) -> str:
        """Delegate complex subtask to specialized subordinate"""
        
        if profile not in self.subordinates or reset:
            subordinate = self.create_subordinate(profile)
            subordinate.set_data("_superior", self.agent)
            self.subordinates[profile] = subordinate
        
        subordinate = self.subordinates[profile]
        result = await subordinate.process(message)
        
        return result
```

#### **1.5.2 Add Inter-Agent Communication** (1-2 days)
```python
# core/agent_communication.py
class AgentCommunication:
    """Enable agents to ask each other for help"""
    
    @staticmethod
    async def ask_agent(from_agent: Agent, to_agent: Agent, question: str) -> str:
        """One agent asks another for information"""
        logger.info(f"{from_agent.name} → {to_agent.name}: {question}")
        
        response = await to_agent.process(question)
        
        return response

# Example: Strategy Agent asks Research Agent
class StrategyAgent:
    async def analyze_pipeline(self):
        # Ask Research Agent for recent research
        research = await AgentCommunication.ask_agent(
            from_agent=self,
            to_agent=research_agent,
            question="What are the top 5 companies researched this week?"
        )
        
        # Synthesize with own analysis
        return self.create_insights(research)
```

#### **1.5.3 Add to Strategy Agent** (1 day)
```python
# agents/strategy_agent.py
class StrategyAgent:
    def __init__(self):
        self.delegation = AgentDelegation(self)
    
    async def handle_complex_request(self, message: str):
        """Handle requests that need task decomposition"""
        
        if "competitor" in message.lower():
            # Delegate competitor analysis to subordinate
            analysis = await self.delegation.call_subordinate(
                profile="competitor_analyst",
                message=f"Analyze: {message}"
            )
            
            # Apply strategic expertise to subordinate's research
            strategy = await self.generate_strategy(analysis)
            return strategy
```

### **Benefits**:
- ✅ **Task Decomposition**: Break complex requests into focused subtasks
- ✅ **Cleaner Contexts**: Each subordinate has focused context
- ✅ **Agent Collaboration**: Agents can ask each other for help
- ✅ **Foundation for Phase 3**: Enables autonomous multi-agent collaboration!

### **Use Case Example**:
```
User: "Compare our pricing to top 3 competitors and suggest changes"

Strategy Agent:
  ↓ spawns subordinate("competitor_analyst", "Competitor A")
  ↓ spawns subordinate("competitor_analyst", "Competitor B")
  ↓ spawns subordinate("competitor_analyst", "Competitor C")
  
  [Each subordinate researches independently using MCP tools + FAISS memory]
  
  ↓ Synthesizes all 3 analyses
  ↓ Applies pricing strategy expertise
  ↓ Returns comprehensive recommendation with specific suggestions
```

**Why after Phase 1?** Subordinates can use ReAct + MCP tools + FAISS memory = WAY more powerful!

---

## **🎯 Phase 2: DSPy Optimization Pipeline**
**Timeline**: Week 5-6  
**Priority**: HIGH  
**Status**: 🟡 PLANNED

### **Goal**:
Auto-improve prompts based on labeled examples and metrics.

### **Implementation**:

#### **2.1 Create Training Dataset**
```python
# training/conversation_examples.py
examples = [
    dspy.Example(
        context=system_state,
        user_message="How many HOT leads?",
        response="You currently have 3 HOT leads...",
        quality_score=5  # User gave thumbs up
    ).with_inputs("context", "user_message"),
    # ... more examples
]
```

#### **2.2 Define Success Metrics**
```python
# training/metrics.py
def conversation_quality(example, prediction):
    """Rate conversation quality 1-5"""
    # Check for:
    # - Accuracy (does it match data?)
    # - Helpfulness (suggested actions?)
    # - Clarity (easy to understand?)
    # - Completeness (answered question?)
    return score

def lead_qualification_accuracy(example, prediction):
    """How often does qualification match manual review?"""
    # Compare DSPy score vs human review
    return accuracy_percentage
```

#### **2.3 Run Optimization**
```python
# training/optimize.py
from dspy.teleprompt import BootstrapFewShot, MIPRO

# Optimize Strategy Agent
optimizer = BootstrapFewShot(
    metric=conversation_quality,
    max_bootstrapped_demos=8
)

optimized_strategy = optimizer.compile(
    strategy_agent,
    trainset=conversation_examples
)

# Save optimized version
optimized_strategy.save("models/strategy_agent_v2.json")
```

#### **2.4 A/B Testing**
- Run old vs optimized in parallel
- Track user satisfaction
- Promote winner to production

---

## **🎯 Phase 3: Autonomous Multi-Agent Collaboration**
**Timeline**: Week 3-5  
**Priority**: VERY HIGH (YOUR KEY REQUEST)

### **Goal**:
Agents work together autonomously when you're asleep, doing:
- Market research
- Business strategy development
- Lead analysis and scoring
- Follow-up email strategy planning
- Competitive intelligence gathering

### **Architecture**:

#### **3.1 Agent Collaboration Framework**
```python
# agents/autonomous/collaboration.py
class AutonomousCollaboration:
    """Manages overnight agent collaboration"""
    
    def __init__(self):
        self.strategy_agent = StrategyAgent()
        self.research_agent = ResearchAgent()
        self.follow_up_agent = FollowUpAgent()
        self.inbound_agent = InboundAgent()
        
        # Collaboration queue
        self.tasks = asyncio.Queue()
        self.results = []
        
    async def nightly_strategy_session(self):
        """Run comprehensive strategy analysis overnight"""
        
        # 1. Strategy Agent proposes research topics
        topics = await self.strategy_agent.propose_research_topics()
        
        # 2. Research Agent investigates each topic
        for topic in topics:
            research = await self.research_agent.deep_research(topic)
            
            # 3. Strategy Agent analyzes findings
            insights = await self.strategy_agent.analyze_research(research)
            
            # 4. Follow-Up Agent adapts email strategy
            email_updates = await self.follow_up_agent.update_strategy(insights)
            
            # 5. Store in Supabase for morning review
            await self.save_insights(insights, email_updates)
        
    async def overnight_lead_analysis(self):
        """Analyze all leads in-depth while you sleep"""
        
        # Get all leads needing research
        leads = await self.get_leads_needing_research()
        
        for lead in leads:
            # Research company deeply
            company_intel = await self.research_agent.company_deep_dive(
                company_name=lead.company_name,
                use_free_models=True  # Cost optimization!
            )
            
            # Strategy reviews and recommends approach
            strategy = await self.strategy_agent.recommend_approach(
                lead=lead,
                intel=company_intel,
                use_free_models=True
            )
            
            # Follow-up creates personalized sequence
            sequence = await self.follow_up_agent.create_sequence(
                lead=lead,
                strategy=strategy,
                use_free_models=True
            )
            
            # Claude 3.5 Sonnet proofreads (paid model)
            final = await self.proofread_with_sonnet(sequence)
            
            # Save for morning
            await self.save_overnight_work(lead, final)
```

#### **3.2 Scheduled Tasks**
```python
# api/schedulers.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Run every night at 2 AM
@scheduler.scheduled_job('cron', hour=2)
async def nightly_agent_collaboration():
    collab = AutonomousCollaboration()
    await collab.nightly_strategy_session()
    await collab.overnight_lead_analysis()
    await collab.market_research()
    
# Morning summary at 8 AM
@scheduler.scheduled_job('cron', hour=8)
async def morning_summary():
    summary = await generate_overnight_summary()
    await send_to_slack(summary)
```

#### **3.3 Example Overnight Workflow**
```
2:00 AM - Strategy Agent: "Let's research competitors tonight"
2:05 AM - Research Agent: "Found 5 competitors, gathering intel..."
2:30 AM - Research Agent: "Intel complete, here are findings..."
2:35 AM - Strategy Agent: "Based on this, we should emphasize X in emails"
2:40 AM - Follow-Up Agent: "Drafted new email angles based on insights"
2:45 AM - Claude 3.5 Sonnet: "Proofread and polished all drafts"
2:50 AM - System: "Saved to Supabase, will notify Josh at 8 AM"

8:00 AM - Slack Message: "Good morning! Last night your agents:
  - Researched 5 competitors
  - Found 3 strategic opportunities
  - Updated 12 email sequences
  - Here's the summary..."
```

---

## **🎯 Phase 4: Cost Optimization Strategy**
**Timeline**: Week 3-4 (parallel with Phase 3)  
**Priority**: HIGH

### **Goal**:
Use free/cheap models for background work, paid models for final quality.

### **Model Tier Strategy**:

#### **4.1 Free Tier (Background Work)**
Use OpenRouter free models with high context:
- **Llama 3.1 70B** (200k context, FREE)
- **Mixtral 8x7B** (32k context, FREE)
- **Qwen 2.5 72B** (128k context, FREE)

**Best for**:
- Market research scraping
- Company intelligence gathering
- Brainstorming email angles
- Competitive analysis
- Lead scoring drafts

#### **4.2 Paid Tier (Quality Check)**
- **Claude 3.5 Sonnet** (200k context, ~$3/M tokens)

**Best for**:
- Final proofreading
- Customer-facing messages
- Critical decisions
- Complex reasoning

#### **4.3 Implementation**
```python
# core/model_selector.py
class ModelSelector:
    """Choose model based on task criticality"""
    
    FREE_MODELS = [
        "openrouter/meta-llama/llama-3.1-70b-instruct",
        "openrouter/mistralai/mixtral-8x7b-instruct",
        "openrouter/qwen/qwen-2.5-72b-instruct"
    ]
    
    PAID_MODEL_LOW = "openrouter/anthropic/claude-haiku-4.5"  # Fast, cheap for routine work
    PAID_MODEL_HIGH = "openrouter/anthropic/claude-sonnet-4.5"  # Premium for complex reasoning
    
    def select_model(self, task_type: str, is_overnight: bool = False, complexity: str = "low") -> str:
        """Select appropriate model based on task and complexity"""
        
        # Overnight work = always free
        if is_overnight:
            return random.choice(self.FREE_MODELS)
        
        # High-complexity customer-facing = Sonnet 4.5
        if complexity == "high" or task_type in ["strategy_analysis", "complex_research", "competitor_analysis"]:
            return self.PAID_MODEL_HIGH
        
        # Standard customer-facing = Haiku 4.5
        if task_type in ["email_to_lead", "slack_response", "qualification", "follow_up"]:
            return self.PAID_MODEL_LOW
        
        # Background = free
        if task_type in ["research", "brainstorm", "analysis", "draft"]:
            return random.choice(self.FREE_MODELS)
        
        # Default = low-tier paid for safety
        return self.PAID_MODEL_LOW

# Use in agents
class ResearchAgent:
    async def deep_research(self, topic: str, use_free: bool = False):
        model = self.model_selector.select_model(
            "research", 
            is_overnight=use_free
        )
        
        # Configure DSPy with selected model
        lm = dspy.LM(model=model, api_key=self.api_key)
        with dspy.context(lm=lm):
            result = self.research_module(topic=topic)
        
        return result
```

#### **4.4 Cost Projection**
```
BEFORE (all Claude 3.5 Sonnet):
- 1M tokens/day overnight work = $3/day = $90/month
- User interactions = $50/month
- TOTAL: $140/month

AFTER (free for overnight, paid for user-facing):
- Overnight work (free models) = $0/month
- Claude proofreading (10% of volume) = $9/month
- User interactions = $50/month  
- TOTAL: $59/month

SAVINGS: $81/month (58% reduction!)
```

---

## **🎯 Phase 5: Zapier MCP Integration**
**Timeline**: Week 5-6  
**Priority**: MEDIUM

### **Goal**:
Integrate Zapier MCP for expanded tool access.

### **Available via Zapier MCP**:
- **Google Workspace** (Sheets, Docs, Calendar)
- **HubSpot** / **Salesforce** integration
- **Twitter** / **LinkedIn** monitoring
- **Airtable** for custom databases
- **Notion** for documentation
- **Calendly** for meeting scheduling
- 5,000+ other apps

### **Implementation**:
```python
# tools/zapier_mcp.py
from mcp import Client

class ZapierTools:
    """Zapier MCP integration"""
    
    def __init__(self):
        self.client = Client(
            server_url=os.getenv("ZAPIER_MCP_URL"),
            api_key=os.getenv("ZAPIER_API_KEY")
        )
    
    @tool
    async def add_to_google_sheet(self, sheet_id: str, data: Dict):
        """Add row to Google Sheet"""
        return await self.client.call_tool(
            "google_sheets_add_row",
            sheet_id=sheet_id,
            data=data
        )
    
    @tool
    async def schedule_calendly_meeting(self, lead_email: str):
        """Send Calendly invite"""
        return await self.client.call_tool(
            "calendly_create_invite",
            email=lead_email
        )
    
    @tool
    async def post_to_linkedin(self, content: str):
        """Post to company LinkedIn"""
        return await self.client.call_tool(
            "linkedin_create_post",
            content=content
        )

# Add to Strategy Agent
self.zapier = ZapierTools()
self.strategy_react = dspy.ReAct(
    signature=StrategyConversation,
    tools=[
        self.zapier.add_to_google_sheet,
        self.zapier.schedule_calendly_meeting,
        self.zapier.post_to_linkedin,
        # ... other tools
    ]
)
```

---

## **🎯 Phase 6: LangGraph Workflow Orchestration**
**Timeline**: Week 6-8  
**Priority**: MEDIUM

### **Goal**:
Use LangGraph for complex multi-agent workflows with branching logic.

### **Example: Lead Qualification Workflow**
```python
from langgraph.graph import StateGraph, END

# Define workflow state
class LeadState(TypedDict):
    lead: Lead
    qualification_score: int
    research_completed: bool
    email_sent: bool
    meeting_scheduled: bool

# Build workflow
workflow = StateGraph(LeadState)

# Add nodes (agents)
workflow.add_node("qualify", inbound_agent.qualify_lead)
workflow.add_node("research", research_agent.research_lead)
workflow.add_node("email", follow_up_agent.send_email)
workflow.add_node("schedule", strategy_agent.schedule_meeting)

# Add conditional edges
workflow.add_conditional_edges(
    "qualify",
    lambda state: "hot" if state["qualification_score"] > 80 else "warm",
    {
        "hot": "schedule",  # HOT leads → immediate meeting
        "warm": "research"  # WARM leads → research first
    }
)

workflow.add_edge("research", "email")
workflow.add_edge("email", END)
workflow.add_edge("schedule", END)

# Compile
app = workflow.compile()

# Run
result = await app.ainvoke({"lead": new_lead})
```

---

## **📋 Complete Feature List**

### **🔴 CRITICAL (Blocking Issues - Must Fix First)**:
- [ ] **PostgreSQL Checkpointer** - Follow-up state currently lost on restart (using MemorySaver)
- [ ] **Research Agent API Keys** - Clearbit, Apollo, Perplexity (currently returning empty)
- [ ] **Real Supabase Queries** - Strategy Agent using mock data
- [ ] **Close CRM Integration** - Currently stub only, needs full implementation

### **🟡 HIGH PRIORITY (Core Functionality)**:
- [ ] Real-time Supabase queries in all agent responses
- [ ] Dynamic pipeline visualization generation
- [ ] Follow-Up Agent status message DSPy formatting
- [ ] Research Agent result formatting with DSPy
- [ ] Close CRM two-way sync (create leads, update status, sync notes)
- [ ] Lead scoring refinement based on outcomes
- [ ] **SMS Integration (Twilio)** - Multi-channel outreach
- [ ] **Response Detection Webhook** - Detect email replies automatically
- [ ] **Rate Limiting** - Protect endpoints from abuse
- [ ] **Request Size Limits** - Security hardening
- [ ] **Circuit Breakers** - Graceful degradation when APIs fail
- [ ] **Deep Lead Research** - Full person/company intelligence

### **🟢 NEW FEATURES (Advanced Capabilities)**:
- [ ] DSPy ReAct agents with tool use
- [ ] DSPy optimization pipeline (BootstrapFewShot, MIPRO)
- [ ] Autonomous multi-agent collaboration (overnight work)
- [ ] Cost optimization (free models + paid proofreading)
- [ ] Scheduled nightly strategy sessions
- [ ] Morning summary reports
- [ ] Zapier MCP integration
- [ ] LangGraph workflow orchestration
- [ ] A/B testing framework for optimized prompts
- [ ] Training dataset collection system
- [ ] Metrics tracking (conversation quality, lead accuracy)

### **🔵 INFRASTRUCTURE (System Improvements)**:
- [ ] **Persistent Agent State** - All agents save state to PostgreSQL
- [ ] **Real-time Analytics Dashboard** - Grafana/Metabase for metrics
- [ ] **Webhook Retry Logic** - Handle failed deliveries
- [ ] **Email Deliverability Monitoring** - Track bounces, spam scores
- [ ] **Lead Deduplication** - Prevent duplicate lead processing
- [ ] **Conversation Threading** - Track full conversation history per lead
- [ ] **Performance Monitoring** - Track API latency, success rates
- [ ] **Error Alerting** - Slack notifications for critical errors
- [ ] **Backup & Recovery** - Automated database backups

### **📱 INTEGRATION EXPANSIONS**:
- [ ] **LinkedIn Integration** - Profile scraping, company research
- [ ] **Twitter/X Integration** - Social listening, engagement tracking
- [ ] **HubSpot Integration** - CRM sync alternative to Close
- [ ] **Calendly Integration** - Automatic meeting scheduling for HOT leads
- [ ] **Notion Integration** - Documentation and knowledge base
- [ ] **Airtable Integration** - Custom lead tracking views
- [ ] **Google Workspace** - Sheets, Docs, Calendar sync

---

## **🎯 Immediate Next Steps**

### **Updated Priorities** (Oct 18, 2025)

Based on Agent Zero audit and current system analysis:

#### **Week 1: Phase 0 - Critical Bug Fixes** 🔴
**Status**: 🔴 NOT STARTED  
**Timeline**: 2-3 days  
**See**: `docs/PHASE_0_CRITICAL_FIXES.md`

**Tasks**:
1. [ ] PostgreSQL Checkpointer (30 min)
2. [ ] Research Agent API Keys (5 min)
3. [ ] Real Supabase Queries (2 hours)
4. [ ] Close CRM Integration (3 hours)
5. [ ] LinkedIn & Company Intel (4 hours)

**Impact**: Stop data loss, show real numbers (59% → 79% operational)

---

#### **Week 2-3: Phase 0.5 - Agent Zero Integration** 🚀
**Status**: 🟡 PLANNED  
**Timeline**: 1-2 weeks  
**See**: Section above in roadmap

**Tasks**:
1. [ ] MCP Client Integration (2-3 days) ⭐⭐⭐⭐⭐
2. [ ] FAISS Vector Memory (1-2 days) ⭐⭐⭐⭐⭐
3. [ ] Instrument System (2-3 days) ⭐⭐⭐⭐

**Impact**: 100+ integrations, semantic memory, unlimited tools

**Why now?** Agent Zero audit revealed production-ready components we can integrate in days vs building from scratch in months!

---

#### **Week 4-5: Phase 1 - DSPy ReAct Agents** 🎯
**Status**: 🟡 PLANNED  
**Timeline**: 1-2 weeks

**Tasks**:
1. [ ] Convert Strategy Agent to ReAct with MCP tools
2. [ ] Convert Research Agent to ReAct
3. [ ] Add tool use to Inbound & Follow-Up

**Impact**: Agents can use real data + external tools

---

#### **Week 5.5: Phase 1.5 - Agent Delegation** 🔄 (NEW!)
**Status**: 🟡 PLANNED  
**Timeline**: 3-4 days

**Tasks**:
1. [ ] Add delegation infrastructure (1 day)
2. [ ] Add inter-agent communication (1-2 days)
3. [ ] Integrate with Strategy Agent (1 day)

**Impact**: Complex task decomposition, agent collaboration, foundation for autonomous work

**Why now?** After Phase 1, subordinates can use ReAct + MCP tools + FAISS memory!

---

#### **Week 6-7: Phase 2 - DSPy Optimization** 🎯
**Status**: 🟡 PLANNED  
**Timeline**: 1 week

**Tasks**:
1. [ ] Create training datasets
2. [ ] Run BootstrapFewShot optimization
3. [ ] A/B test optimized vs original
4. [ ] Deploy optimized agents

**Impact**: Auto-improving agents based on real data

---

#### **Week 7-9: Phases 3 & 4 - Your Original Request** 💡
**Status**: 🟡 PLANNED  
**Timeline**: 2-3 weeks

**Tasks**:
1. [ ] Autonomous collaboration framework (Phase 3)
2. [ ] Cost optimization (Phase 4)
3. [ ] Nightly scheduled tasks
4. [ ] Overnight agent collaboration

**Impact**: Agents work while you sleep, 50% cost reduction

**Now powered by**: Delegation + Inter-agent communication + MCP tools + Memory!

---

### **Why This Order Changed?**

**Original Plan**: Phase 3 & 4 first (autonomous collaboration)  
**Updated Plan**: Phase 0 → 0.5 → 1 → 1.5 → 2 → 3 & 4

**Reason**: Agent Zero audit revealed TWO game-changers:

1. **Infrastructure we can integrate fast**:
   - **100+ integrations** in 2-3 days (MCP client)
   - **Semantic memory** in 1-2 days (FAISS)
   - **Unlimited tools** in 2-3 days (Instruments)

2. **Agent delegation pattern** (NEW!):
   - **Task decomposition** via subordinate agents
   - **Inter-agent communication** for collaboration
   - **Foundation for autonomous work**

**Key Insight**: By adding Phase 1.5 (delegation) AFTER Phase 1 (ReAct), subordinates can:
- Use MCP tools (100+ integrations)
- Access FAISS memory (learn & recall)
- Execute multi-step reasoning (ReAct)

This makes autonomous collaboration (Phase 3) WAY more powerful!

---

## **💰 Budget Planning**

### **Current Costs**:
- OpenRouter API: ~$140/month (all Claude 3.5 Sonnet)
- Railway hosting: $20/month
- Supabase: $0/month (free tier)
- **TOTAL: ~$160/month**

### **After Phase 4 (Cost Optimization)**:
- OpenRouter API: ~$59/month (mostly free models)
- Railway hosting: $20/month
- Supabase: $0/month
- **TOTAL: ~$79/month**
- **SAVINGS: $81/month (51% reduction)**

### **After All Phases**:
- OpenRouter API: ~$80/month (with heavy overnight use)
- Railway hosting: $20/month
- Supabase: $25/month (upgraded for more data)
- Zapier MCP: $30/month
- **TOTAL: ~$155/month**
- Still cheaper + way more value!

---

## **📊 Success Metrics**

### **Phase 3 Success** (Autonomous Collaboration):
- [ ] Agents complete 5+ research tasks overnight
- [ ] Morning summaries delivered by 8 AM
- [ ] Strategy insights saved to Supabase
- [ ] Email sequences updated autonomously
- [ ] Zero crashes during overnight runs

### **Phase 4 Success** (Cost Optimization):
- [ ] API costs reduced by 50%
- [ ] Quality maintained (user satisfaction > 4/5)
- [ ] Free models handle 80%+ of background work
- [ ] Claude 3.5 Sonnet only for final touches

### **Overall Success**:
- [ ] Agents autonomously improve over time (optimization working)
- [ ] Multi-agent collaboration produces valuable insights
- [ ] Cost per lead decreases
- [ ] Conversion rates increase
- [ ] Time saved on manual research/strategy

---

## **🚀 Next Actions**

### **Recommended Start: Phase 0** (Critical Fixes)

**Why start here?**
- Currently losing follow-up state on every restart
- Research agent returning empty (no API keys)
- Strategy agent showing fake numbers (mock data)
- Only takes 2-3 days to fix

**After Phase 0**: System is solid, data is real, no more losses.

---

### **Then: Phase 0.5** (Agent Zero Integration)

**Why this is huge**:
- MCP client: 100+ integrations in 2-3 days (vs months to build)
- FAISS memory: Agents learn from every interaction
- Instruments: Unlimited tools without prompt bloat

**After Phase 0.5**: You have a supercharged system with massive capability.

---

### **Then: Phase 1** (DSPy ReAct)

**Why now it's better**:
- ReAct agents can use MCP tools (100+ integrations!)
- Can store results in FAISS memory
- Can discover instruments semantically

**After Phase 1**: Agents are tool-using powerhouses.

---

### **Finally: Phases 3 & 4** (Your Original Vision)

**Why last**:
- Autonomous collaboration is MORE powerful with MCP + memory + tools
- Agents have way more capabilities to collaborate with
- Cost optimization has more models to choose from

**After All Phases**: Agents work overnight with 100+ tools, learning from everything, costing 50% less!

---

## **📝 Changelog**

### **October 18, 2025 - PM Update**
- ✅ Analyzed Agent Zero's `call_subordinate` delegation pattern
- ✅ Created comprehensive delegation analysis document
- ✅ Added Phase 1.5 (Agent Delegation & Communication)
- ✅ Updated roadmap timeline to include delegation
- ✅ Documented inter-agent communication architecture
- ✅ Identified delegation as foundation for autonomous collaboration

### **October 18, 2025 - AM Update**
- ✅ Fixed DSPy configuration (LM not loaded error)
- ✅ Fixed OpenRouter API integration (405 error)
- ✅ Fixed AttributeError with optional output fields
- ✅ Completed Agent Zero framework audit (5000+ lines)
- ✅ Identified MCP client for integration
- ✅ Created Phase 0 (critical fixes) document
- ✅ Added Phase 0.5 (Agent Zero integration)
- ✅ Updated roadmap priorities

**Next**: Start Phase 0 implementation

---

**Ready to start Phase 0?** 🛠️
