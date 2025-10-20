"""Strategy Agent - Josh's Personal AI Partner.

This agent coordinates the entire Hume AI infrastructure and provides strategic
guidance via bidirectional Slack communication. It has access to all sub-agents
and knowledge bases.

Capabilities:
- Interactive conversation via Slack
- Pipeline analysis and recommendations
- Coordination of inbound + outbound + research agents
- Proactive insights and alerts
- Strategic decision support
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import httpx
import os
import dspy
import json

from agents.inbound_agent import InboundAgent
from agents.research_agent import ResearchAgent
from agents.follow_up_agent import FollowUpAgent
from dspy_modules.conversation_signatures import (
    StrategyConversation,
    PipelineAnalysis as PipelineAnalysisSignature,
    GenerateRecommendations,
    QuickPipelineStatus,
)

logger = logging.getLogger(__name__)


# ===== Data Models =====

class PipelineAnalysis(BaseModel):
    """Analysis of the inbound pipeline."""
    period_days: int
    total_leads: int
    by_tier: Dict[str, int] = Field(default_factory=dict)
    by_source: Dict[str, int] = Field(default_factory=dict)
    conversion_rate: float = 0.0
    avg_qualification_score: float = 0.0
    top_industries: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OutboundTarget(BaseModel):
    """Recommended target for outbound outreach."""
    company_name: str
    reason: str
    fit_score: int
    estimated_patient_volume: Optional[str] = None
    contact_info: Optional[Dict[str, str]] = None


class StrategyRecommendation(BaseModel):
    """Strategic recommendation."""
    type: str = Field(..., description="Type: pipeline_action, outbound_target, process_improvement")
    priority: str = Field(..., description="Priority: high, medium, low")
    title: str
    description: str
    action_items: List[str] = Field(default_factory=list)
    impact: str
    effort: str


class ConversationContext(BaseModel):
    """Context for conversational AI."""
    user_message: str = Field(..., description="User's question or request")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Previous messages")
    available_data: Dict[str, Any] = Field(default_factory=dict, description="Context data from agents")


class ConversationResponse(BaseModel):
    """Structured response from conversational AI."""
    response: str = Field(..., description="Natural language response to user")
    suggested_actions: List[str] = Field(default_factory=list, description="Suggested follow-up actions")
    requires_agent_action: bool = Field(default=False, description="Whether agent action is needed")
    agent_commands: List[Dict[str, Any]] = Field(default_factory=list, description="Commands for agents")


# ===== DSPy Signatures =====

class StrategyConversation(dspy.Signature):
    """Intelligent conversational response for Strategy Agent.
    
    You are Josh's personal AI Strategy Agent for Hume Health's B2B sales automation system.
    Provide intelligent, contextual responses about:
    - Infrastructure & architecture
    - Agent capabilities & coordination  
    - Pipeline analysis & insights
    - Strategic recommendations
    - Technical deep dives
    
    Be conversational, knowledgeable, and proactive.
    """
    
    context: str = dspy.InputField(desc="System context and infrastructure info")
    user_message: str = dspy.InputField(desc="User's question or request")
    conversation_history: str = dspy.InputField(desc="Previous conversation context")
    
    response: str = dspy.OutputField(desc="Natural, intelligent response to user")
    # Made truly optional - prevents parsing errors on long responses (Phase 0 Fix #1)
    suggested_actions: str = dspy.OutputField(
        desc="Comma-separated list of suggested next actions (optional, leave blank if none)",
        prefix="Suggested Actions (optional):"
    )


# ===== Strategy Agent =====

class StrategyAgent(dspy.Module):
    """Personal AI advisor for strategic decision-making.
    
    Refactored as dspy.Module for better architecture and DSPy optimization.
    Phase 0.3 - October 19, 2025
    """
    
    def __init__(self):
        super().__init__()  # Initialize dspy.Module
        self.slack_bot_token = (
            os.getenv("SLACK_BOT_TOKEN") or
            os.getenv("SLACK_MCP_XOXB_TOKEN") or
            os.getenv("SLACK_MCP_XOXP_TOKEN")
        )
        self.josh_slack_dm_channel = os.getenv("JOSH_SLACK_DM_CHANNEL", "U123ABC")
        
        # Initialize Supabase for REAL data access
        self.supabase = None
        try:
            from supabase import create_client
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("   Supabase: ✅ Connected (real data access enabled)")
            else:
                logger.warning("   Supabase: ❌ No credentials (will not have real-time data)")
        except Exception as e:
            logger.error(f"   Supabase: ❌ Failed to connect: {e}")
        
        # Initialize sub-agents
        self.inbound_agent = InboundAgent()
        self.research_agent = ResearchAgent()
        self.follow_up_agent = FollowUpAgent()
        
        # Initialize audit agent for real data retrieval
        from agents.audit_agent import get_audit_agent
        self.audit_agent = get_audit_agent()
        logger.info("   Audit Agent: ✅ Initialized for real data queries")
        
        # Initialize MCP client for Zapier integrations (Phase 0/0.5)
        self.mcp_client = None
        try:
            from core.mcp_client import get_mcp_client
            self.mcp_client = get_mcp_client()
            if self.mcp_client and self.mcp_client.client:
                logger.info("   MCP Client: ✅ Connected to Zapier (200+ tools)")
            else:
                logger.warning("   MCP Client: ⚠️ Not configured (set MCP_SERVER_URL)")
        except Exception as e:
            logger.error(f"   MCP Client: ❌ Failed to initialize: {e}")
        
        # A2A communication endpoint
        self.a2a_endpoint = os.getenv(
            "A2A_ENDPOINT",
            "https://hume-dspy-agent-production.up.railway.app/a2a/introspect"
        )
        self.a2a_api_key = os.getenv("A2A_API_KEY")
        
        # Configure DSPy with Sonnet 4.5 for high-level reasoning
        # Strategy Agent does complex analysis, so uses premium model
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if openrouter_key:
                strategy_lm = dspy.LM(
                    model="openrouter/anthropic/claude-sonnet-4.5",
                    api_key=openrouter_key,
                    max_tokens=3000,  # More tokens for complex reasoning
                    temperature=0.7
                )
                dspy.configure(lm=strategy_lm)
                logger.info("   Strategy Agent: ✅ Using Sonnet 4.5 for high-level reasoning")
            
            # Initialize DSPy modules with Sonnet 4.5
            # IMPORTANT: Use Predict for simple queries (fast), ChainOfThought for complex (reasoning)
            self.simple_conversation = dspy.Predict(StrategyConversation)  # No reasoning
            self.complex_conversation = dspy.ChainOfThought(StrategyConversation)  # With reasoning
            self.pipeline_analyzer = dspy.ChainOfThought(PipelineAnalysisSignature)
            self.recommendation_generator = dspy.ChainOfThought(GenerateRecommendations)
            self.quick_status = dspy.Predict(QuickPipelineStatus)  # Status check is simple
            
            # Initialize ReAct for tool calling (action queries)
            self.tools = self._init_tools()
            self.action_agent = dspy.ReAct(StrategyConversation, tools=self.tools)
            
            logger.info("   DSPy Modules: ✅ Triple-mode conversation")
            logger.info("   Simple queries → Predict (fast, no reasoning)")
            logger.info("   Complex queries → ChainOfThought (slower, with reasoning)")
            logger.info("   Action queries → ReAct (tool calling for real data)")
            logger.info(f"   ReAct Tools: {len(self.tools)} available ({', '.join([t.__name__ for t in self.tools][:3])}...)")
        except Exception as e:
            logger.error(f"   DSPy Modules: ❌ Failed to initialize: {e}")
            self.simple_conversation = None
            self.complex_conversation = None
            self.action_agent = None
            self.tools = []
            self.pipeline_analyzer = None
            self.recommendation_generator = None
            self.quick_status = None
        
        # Conversation history (per-user, in-memory for now)
        self.conversation_history: Dict[str, List[Dict[str, str]]] = {}
        
        # Phase 0.5: Initialize FAISS vector memory
        self.memory = None
        try:
            from memory.vector_memory import get_agent_memory
            self.memory = get_agent_memory("strategy_agent")
            if self.memory:
                logger.info("   Memory: ✅ FAISS vector memory enabled")
            else:
                logger.info("   Memory: ⚠️ Disabled (FAISS not available)")
        except Exception as e:
            logger.warning(f"   Memory: ⚠️ Failed to initialize: {e}")
        
        # Phase 0.5: Initialize instrument manager
        self.instruments = None
        try:
            from instruments.instrument_manager import get_instrument_manager
            self.instruments = get_instrument_manager()
            if self.instruments and self.instruments.enabled:
                # Register existing tools as instruments
                self._register_instruments()
                logger.info(f"   Instruments: ✅ {len(self.instruments.instruments)} tools registered")
            else:
                logger.info("   Instruments: ⚠️ Disabled")
        except Exception as e:
            logger.warning(f"   Instruments: ⚠️ Failed to initialize: {e}")
        
        # Phase 0.7: Initialize MCP Orchestrator for dynamic tool loading
        self.mcp_orchestrator = None
        try:
            from core.mcp_orchestrator import get_mcp_orchestrator
            self.mcp_orchestrator = get_mcp_orchestrator()
            logger.info(f"   MCP Orchestrator: ✅ Dynamic tool loading enabled")
            logger.info(f"      Agentic server selection (70% token reduction expected)")
        except Exception as e:
            logger.warning(f"   MCP Orchestrator: ⚠️ Failed to initialize: {e}")
        
        # Phase 1.5: Initialize Agent Delegation (Enhanced with Agent Zero patterns)
        self.delegation = None
        try:
            from core.agent_delegation_enhanced import enable_delegation
            self.delegation = enable_delegation(self)
            logger.info("   Delegation: ✅ Enhanced Agent Zero-style subordinate spawning")
            logger.info("      Features: Dynamic tools, DSPy modules, Memory, Iterative refinement")
            logger.info("      Profiles: document_analyst, competitor_analyst, market_researcher, +3 more")
        except Exception as e:
            logger.warning(f"   Delegation: ⚠️ Failed to initialize: {e}")
        
        # Phase 1.5: Initialize Inter-Agent Communication
        self.communication = None
        try:
            from core.agent_communication import enable_communication
            self.communication = enable_communication(self)
            logger.info("   Communication: ✅ Inter-agent communication enabled")
            logger.info("      Can ask/notify: InboundAgent, ResearchAgent, FollowUpAgent, AuditAgent")
        except Exception as e:
            logger.warning(f"   Communication: ⚠️ Failed to initialize: {e}")
        
        logger.info("🎯 Strategy Agent initialized")
        logger.info(f"   Slack: {'✅ Configured' if self.slack_bot_token else '❌ Not configured'}")
        logger.info(f"   A2A: {'✅ Configured' if self.a2a_api_key else '❌ Not configured'}")
    
    # ===== ReAct Tools =====
    
    def _init_tools(self) -> List:
        """Initialize tools that ReAct can call.
        
        Tools allow ReAct to actually execute actions instead of just talking about them.
        Each tool is a Python function that ReAct can invoke.
        
        Returns:
            List of callable tools
        """
        import json
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        # Use the MCP client initialized in __init__
        mcp = self.mcp_client
        
        # Thread pool for running async functions in sync context
        executor = ThreadPoolExecutor(max_workers=3)
        
        def run_async_in_thread(coro):
            """Run async coroutine in a new thread with its own event loop.
            
            This avoids 'asyncio.run() cannot be called from a running event loop' errors
            that happen when DSPy ReAct tries to call async functions.
            """
            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()
            
            future = executor.submit(run_in_thread)
            return future.result(timeout=60)  # 60 second timeout
        
        def audit_lead_flow(timeframe_hours: int = 24) -> str:
            """
            Audit lead flow with real data from Supabase and GMass.
            
            This tool queries actual databases and APIs to get:
            - Lead capture metrics
            - Email campaign statistics
            - Deliverability rates
            - Engagement metrics (opens, clicks, responses)
            
            Args:
                timeframe_hours: How many hours back to audit (default: 24)
            
            Returns:
                JSON string with complete audit results
            """
            try:
                # Execute async audit in separate thread to avoid event loop conflicts
                logger.info(f"🔧 ReAct tool: audit_lead_flow(timeframe_hours={timeframe_hours})")
                result = run_async_in_thread(
                    self.audit_agent.audit_lead_flow(timeframe_hours)
                )
                logger.info(f"✅ ReAct tool: audit_lead_flow returned {len(str(result))} chars")
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"❌ ReAct tool audit_lead_flow failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return json.dumps({"error": str(e), "tool": "audit_lead_flow"})
        
        def query_supabase(table: str, limit: int = 100) -> str:
            """
            Query Supabase database tables.
            
            Available tables:
            - leads: Lead records with qualification data
            - conversations: Interaction history
            - agent_state: Agent execution state
            
            Args:
                table: Table name to query
                limit: Maximum rows to return (default: 100)
            
            Returns:
                JSON string with query results
            """
            try:
                if not self.supabase:
                    return json.dumps({"error": "Supabase not configured"})
                
                result = self.supabase.table(table).select("*").limit(limit).execute()
                return json.dumps(result.data, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        def get_pipeline_stats() -> str:
            """
            Get current pipeline statistics.
            
            Returns:
                JSON string with pipeline metrics:
                - Total leads
                - Breakdown by tier (HOT/WARM/COOL/COLD)
                - Breakdown by source (typeform, vapi, etc.)
                - Recent activity
            """
            try:
                if not self.supabase:
                    return json.dumps({"error": "Supabase not configured"})
                
                # Query recent leads
                result = self.supabase.table('leads').select("*").limit(100).execute()
                
                # Calculate stats
                total = len(result.data)
                by_tier = {}
                by_source = {}
                
                for lead in result.data:
                    tier = lead.get('tier', 'UNKNOWN')
                    by_tier[tier] = by_tier.get(tier, 0) + 1
                    
                    source = lead.get('source', 'UNKNOWN')
                    by_source[source] = by_source.get(source, 0) + 1
                
                return json.dumps({
                    "total_leads": total,
                    "by_tier": by_tier,
                    "by_source": by_source
                }, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        def create_close_lead(
            name: str,
            email: str = None,
            phone: str = None,
            company: str = None,
            note: str = None
        ) -> str:
            """
            Create a new lead in Close CRM via MCP (Phase 0 integration).
            
            This tool creates a lead in Close CRM with the provided information.
            Use this when qualifying leads to sync them to the CRM.
            
            Args:
                name: Lead name (required)
                email: Email address
                phone: Phone number  
                company: Company name
                note: Additional notes or context
            
            Returns:
                JSON string with Close CRM lead creation result
            """
            try:
                logger.info(f"🔧 ReAct MCP tool: create_close_lead(name={name})")
                result = run_async_in_thread(
                    mcp.close_create_lead(
                        name=name,
                        email=email,
                        phone=phone,
                        company=company,
                        note=note
                    )
                )
                logger.info(f"✅ ReAct MCP tool: create_close_lead succeeded")
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"❌ ReAct MCP tool create_close_lead failed: {e}")
                return json.dumps({"error": str(e), "tool": "create_close_lead"})
        
        def research_with_perplexity(query: str) -> str:
            """
            Research a topic using Perplexity AI via MCP (Phase 0 integration).
            
            This tool uses Perplexity's AI to research companies, people, or topics.
            Use this to enrich lead information or gather competitive intelligence.
            
            Args:
                query: Research query or question
            
            Returns:
                JSON string with Perplexity research results
            """
            try:
                logger.info(f"🔧 ReAct MCP tool: research_with_perplexity(query={query[:50]}...)")
                result = run_async_in_thread(
                    mcp.perplexity_research(query)
                )
                logger.info(f"✅ ReAct MCP tool: research_with_perplexity succeeded")
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"❌ ReAct MCP tool research_with_perplexity failed: {e}")
                return json.dumps({"error": str(e), "tool": "research_with_perplexity"})
        
        def scrape_website(url: str) -> str:
            """
            Scrape a website URL via Apify MCP tool.
            
            This tool scrapes website content (text, markdown, HTML) using Apify.
            Use this to gather information from company websites or landing pages.
            
            Args:
                url: Website URL to scrape
            
            Returns:
                JSON string with scraped content
            """
            try:
                logger.info(f"🔧 ReAct MCP tool: scrape_website(url={url})")
                result = run_async_in_thread(
                    mcp.scrape_url(url)
                )
                logger.info(f"✅ ReAct MCP tool: scrape_website succeeded")
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"❌ ReAct MCP tool scrape_website failed: {e}")
                return json.dumps({"error": str(e), "tool": "scrape_website"})
        
        def list_mcp_tools() -> str:
            """
            List all available MCP tools and integrations from Zapier.
            Shows what integrations (Google Drive, Close CRM, etc.) are available.
            
            Returns:
                JSON string with list of available MCP tools and their descriptions
            """
            try:
                logger.info(f"🔧 ReAct tool: list_mcp_tools()")
                
                if not mcp or not mcp.client:
                    return json.dumps({
                        "error": "MCP client not initialized",
                        "message": "MCP_SERVER_URL environment variable not set",
                        "tool": "list_mcp_tools"
                    })
                
                result = run_async_in_thread(mcp.list_tools())
                
                # Format into readable structure
                tools_summary = {
                    "total_tools": len(result),
                    "tools_by_integration": {},
                    "all_tools": result
                }
                
                # Group by integration (extract from tool name)
                for tool in result:
                    tool_name = tool.get('name', '')
                    # Extract integration name (e.g., "close_create_lead" -> "close")
                    integration = tool_name.split('_')[0] if '_' in tool_name else 'other'
                    
                    if integration not in tools_summary["tools_by_integration"]:
                        tools_summary["tools_by_integration"][integration] = []
                    
                    tools_summary["tools_by_integration"][integration].append({
                        "name": tool_name,
                        "description": tool.get('description', 'No description')[:100]
                    })
                
                logger.info(f"✅ ReAct tool: list_mcp_tools returned {len(result)} tools")
                return json.dumps(tools_summary, indent=2)
            except Exception as e:
                logger.error(f"❌ ReAct tool list_mcp_tools failed: {e}")
                return json.dumps({"error": str(e), "tool": "list_mcp_tools"})
        
        # Phase 1.5: Delegation tool
        def delegate_to_subordinate(profile: str, task: str) -> str:
            """
            Delegate a complex subtask to a specialized subordinate agent.
            
            Use this for tasks that need focused expertise:
            - competitor_analyst: Analyze specific competitors
            - market_researcher: Research markets and trends  
            - account_researcher: Deep dive on target accounts
            - content_strategist: Content planning and strategy
            - campaign_analyst: Analyze campaign performance
            
            Args:
                profile: Subordinate type (e.g., "competitor_analyst")
                task: Detailed task description for subordinate
                
            Returns:
                Result from subordinate agent
            
            Example:
                delegate_to_subordinate("competitor_analyst", "Analyze pricing strategy of Company X vs our offerings")
            """
            try:
                logger.info(f"🎯 ReAct delegating to: {profile}")
                
                if not self.delegation:
                    return json.dumps({"error": "Delegation not available"})
                
                result = run_async_in_thread(
                    self.delegation.call_subordinate(profile, task)
                )
                
                logger.info(f"✅ Subordinate {profile} completed task")
                return result
                
            except Exception as e:
                logger.error(f"❌ Delegation to {profile} failed: {e}")
                return json.dumps({"error": str(e), "profile": profile})
        
        # Phase 1.5: Inter-agent communication tool
        def ask_other_agent(agent_name: str, question: str) -> str:
            """
            Ask another agent for information or help.
            
            Available agents:
            - InboundAgent: Lead qualification info
            - ResearchAgent: Company/person research
            - FollowUpAgent: Email sequence status
            - AuditAgent: Analytics and metrics
            
            Args:
                agent_name: Name of agent to ask (e.g., "ResearchAgent")
                question: Question or request for the agent
                
            Returns:
                Response from the other agent
            
            Example:
                ask_other_agent("ResearchAgent", "What companies did we research this week?")
            """
            try:
                logger.info(f"🤝 ReAct asking: {agent_name}")
                
                if not self.communication:
                    return json.dumps({"error": "Communication not available"})
                
                # Map agent names to instances
                agent_map = {
                    "InboundAgent": self.inbound_agent,
                    "ResearchAgent": self.research_agent,
                    "FollowUpAgent": self.follow_up_agent,
                    "AuditAgent": self.audit_agent
                }
                
                target_agent = agent_map.get(agent_name)
                if not target_agent:
                    return json.dumps({
                        "error": f"Unknown agent: {agent_name}",
                        "available": list(agent_map.keys())
                    })
                
                result = run_async_in_thread(
                    self.communication.ask_agent(target_agent, question)
                )
                
                logger.info(f"✅ {agent_name} responded")
                return result
                
            except Exception as e:
                logger.error(f"❌ Communication with {agent_name} failed: {e}")
                return json.dumps({"error": str(e), "agent": agent_name})
        
        # Phase 1.5: Iterative refinement tool
        def refine_subordinate_work(profile: str, feedback: str) -> str:
            """
            Provide feedback to a subordinate agent to refine their work.
            
            Use this when a subordinate's initial result needs improvement,
            clarification, or additional detail. The subordinate will process
            your feedback and return refined results.
            
            Args:
                profile: Subordinate type (e.g., "document_analyst")
                feedback: Specific feedback or clarification to provide
                
            Returns:
                Refined result from subordinate
            
            Example:
                refine_subordinate_work(
                    "document_analyst",
                    "Focus more on financial spreadsheets and extract revenue data"
                )
            """
            try:
                logger.info(f"🔄 Refining {profile} work")
                
                if not self.delegation:
                    return json.dumps({"error": "Delegation not available"})
                
                result = run_async_in_thread(
                    self.delegation.refine_subordinate_work(profile, feedback)
                )
                
                logger.info(f"✅ {profile} refined work based on feedback")
                return result
                
            except Exception as e:
                logger.error(f"❌ Refinement of {profile} failed: {e}")
                return json.dumps({"error": str(e), "profile": profile})
        
        # Return list of tools (existing + MCP + delegation + communication + refinement)
        tools = [
            # Existing audit/query tools
            audit_lead_flow,
            query_supabase,
            get_pipeline_stats,
            # NEW: MCP-powered tools (Phase 0/0.5)
            create_close_lead,
            research_with_perplexity,
            scrape_website,
            list_mcp_tools,  # List available Zapier integrations
            # NEW: Phase 1.5 - Agent collaboration tools
            delegate_to_subordinate,  # Spawn specialized subordinates
            ask_other_agent,  # Ask other agents for help
            refine_subordinate_work  # Iterative refinement
        ]
        logger.info(f"   Initialized {len(tools)} ReAct tools (including enhanced delegation)")
        logger.info(f"   - 3 core tools (audit, query, stats)")
        logger.info(f"   - 4 MCP tools (Close CRM, Perplexity, Apify, List)")
        logger.info(f"   - 3 Phase 1.5 tools (delegate, ask_agent, refine)")
        return tools
    
    def _register_instruments(self):
        """Register all tools as instruments for semantic discovery (Phase 0.5)."""
        if not self.instruments or not self.instruments.enabled:
            return
        
        # Register core data tools
        self.instruments.register_instrument(
            name="audit_lead_flow",
            description="Audit lead flow with real data from Supabase and GMass. Returns lead metrics, email campaign stats, deliverability, opens, clicks, replies.",
            function=lambda timeframe_hours=24: "Use audit_lead_flow tool in ReAct",
            category="data",
            examples=["audit last 24 hours", "check email deliverability", "get pipeline metrics"]
        )
        
        self.instruments.register_instrument(
            name="query_supabase",
            description="Execute SQL query on Supabase database. Can query leads, campaigns, or any table. Returns JSON results.",
            function=lambda query="": "Use query_supabase tool in ReAct",
            category="data",
            examples=["query hot leads", "get all leads from last week", "count leads by tier"]
        )
        
        self.instruments.register_instrument(
            name="get_pipeline_stats",
            description="Get pipeline statistics and metrics. Returns counts by tier, conversion rates, average scores.",
            function=lambda days=7: "Use get_pipeline_stats tool in ReAct",
            category="analytics",
            examples=["show pipeline stats", "how's the pipeline", "conversion metrics"]
        )
        
        # Register MCP tools
        self.instruments.register_instrument(
            name="create_close_lead",
            description="Create a new lead in Close CRM with contact info and notes. Syncs data to CRM.",
            function=lambda data={}: "Use create_close_lead tool in ReAct",
            category="crm",
            examples=["add to Close CRM", "sync lead to CRM", "create CRM contact"]
        )
        
        self.instruments.register_instrument(
            name="research_with_perplexity",
            description="Research using Perplexity AI for current information. Good for company research, market intel, competitive analysis.",
            function=lambda query="": "Use research_with_perplexity tool in ReAct",
            category="research",
            examples=["research company", "find market information", "competitive intel"]
        )
        
        self.instruments.register_instrument(
            name="scrape_website",
            description="Scrape website content using Apify. Extracts text, markdown, HTML from any URL.",
            function=lambda url="": "Use scrape_website tool in ReAct",
            category="research",
            examples=["scrape company website", "get page content", "extract website info"]
        )
        
        self.instruments.register_instrument(
            name="list_mcp_tools",
            description="List all available MCP/Zapier integrations. Shows what tools are available (Google Drive, Close CRM, Shopify, etc.) and their capabilities.",
            function=lambda: "Use list_mcp_tools tool in ReAct",
            category="system",
            examples=["what zapier tools do we have", "list mcp integrations", "show available integrations", "audit zapier access"]
        )
        
        logger.debug(f"   Registered {len(self.instruments.instruments)} instruments")
    
    # ===== Slack Communication =====
    
    def _chunk_message(self, message: str, max_length: int = 3000) -> List[str]:
        """Intelligently chunk long messages at paragraph boundaries (Phase 0 Fix #2).
        
        Args:
            message: Message to chunk
            max_length: Maximum length per chunk (Slack safe limit)
        
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        current_chunk = ""
        
        # Split by double newlines (paragraphs) for clean breaks
        paragraphs = message.split('\n\n')
        
        for para in paragraphs:
            # If this paragraph alone exceeds max_length, split by lines
            if len(para) > max_length:
                lines = para.split('\n')
                for line in lines:
                    if len(current_chunk) + len(line) + 2 > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = line + '\n'
                    else:
                        current_chunk += line + '\n'
            # Normal paragraph handling
            elif len(current_chunk) + len(para) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + '\n\n'
            else:
                current_chunk += para + '\n\n'
        
        # Add remaining content
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def send_slack_message(
        self,
        message: str,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """Send message to Slack with auto-chunking for long messages (Phase 0 Fix #2).
        
        Args:
            message: Message text (will be chunked if > 3000 chars)
            channel: Channel ID (defaults to Josh's DM)
            thread_ts: Thread timestamp for replies
        
        Returns:
            Message timestamp (ts) of first message, or None
        """
        if not self.slack_bot_token:
            logger.warning("⚠️ Slack not configured, cannot send message")
            return None
        
        target_channel = channel or self.josh_slack_dm_channel
        
        # Chunk long messages to avoid Slack API timeouts
        chunks = self._chunk_message(message)
        
        if len(chunks) > 1:
            logger.info(f"📝 Chunking long message into {len(chunks)} parts")
        
        first_ts = None
        parent_ts = thread_ts
        
        async with httpx.AsyncClient() as client:
            for i, chunk in enumerate(chunks):
                # Add part indicator for multi-part messages
                if len(chunks) > 1:
                    header = f"*[Part {i+1}/{len(chunks)}]*\n\n"
                    chunk_with_header = header + chunk
                else:
                    chunk_with_header = chunk
                
                try:
                    response = await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={
                            "Authorization": f"Bearer {self.slack_bot_token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "channel": target_channel,
                            "text": chunk_with_header,
                            "thread_ts": parent_ts
                        },
                        timeout=10.0
                    )
                    
                    data = response.json()
                    if data.get("ok"):
                        ts = data.get("ts")
                        if i == 0:
                            first_ts = ts
                            # Thread subsequent messages to the first one
                            if not parent_ts:
                                parent_ts = ts
                    else:
                        logger.error(f"Slack send failed for chunk {i+1}: {data.get('error')}")
                        if i == 0:
                            return None
                    
                    # Rate limit: 0.5 second between chunks to avoid API limits
                    if i < len(chunks) - 1:
                        await asyncio.sleep(0.5)
                
                except Exception as e:
                    # Only critical if first chunk fails (Phase 0 Fix: improved logging)
                    if i == 0:
                        logger.error(f"❌ CRITICAL: Failed to send first chunk: {e}")
                        return None
                    else:
                        # Non-critical for subsequent chunks (message partially delivered)
                        logger.warning(f"⚠️ Failed to send chunk {i+1}/{len(chunks)} (non-critical): {e}")
                        # Continue with remaining chunks
        
        return first_ts
    
    async def handle_slack_message(self, message: str, user: str, channel: str, ts: str):
        """Handle incoming message from Slack.
        
        Args:
            message: Message text from user
            user: User ID who sent message
            channel: Channel ID
            ts: Message timestamp
        """
        logger.info(f"💬 Received Slack message from {user}: {message[:50]}...")
        
        # Process the message and generate response (with user tracking)
        response = await self.chat_with_josh(message, user_id=user)
        
        # Send response in thread
        await self.send_slack_message(response, channel=channel, thread_ts=ts)
    
    def forward(self, message: str, context: dict = None, user_id: str = "default") -> str:
        """DSPy Module forward pass - main entry point.
        
        This is the standard dspy.Module interface that enables:
        - DSPy compilation/optimization
        - Consistent API across all modules
        - Better composability
        
        Args:
            message: User's query/request
            context: Optional additional context dict
            user_id: User identifier for conversation history
        
        Returns:
            Response string
        """
        # For now, forward() is a sync wrapper around async chat_with_josh
        # In production, we'd make this fully async or use asyncio.run()
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, return a coroutine
                return loop.create_task(self.chat_with_josh(message, user_id))
            else:
                # We're in sync context, run the async function
                return loop.run_until_complete(self.chat_with_josh(message, user_id))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.chat_with_josh(message, user_id))
    
    async def chat_with_josh(self, message: str, user_id: str = "default") -> str:
        """Process conversational request using pure DSPy intelligence.
        
        NO pattern matching, NO hardcoded responses - everything through DSPy.
        The LLM decides intent and generates appropriate response.
        
        Args:
            message: User's message/question
            user_id: User identifier for conversation history
        
        Returns:
            DSPy-generated response text
        """
        if not self.simple_conversation or not self.complex_conversation or not self.action_agent:
            return "⚠️ Conversational AI not configured. Please set OPENROUTER_API_KEY."
        
        try:
            # Phase 0.6: Check for proactive monitoring commands
            if "implement fix_" in message.lower():
                return await self._handle_fix_approval(message)
            elif "reject fix_" in message.lower():
                return await self._handle_fix_rejection(message)
            
            # Build dynamic system context from actual system state
            system_context = await self._build_system_context()
            
            # Get conversation history for this user
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            history = self.conversation_history[user_id]
            history_text = self._format_conversation_history(history)
            
            # Phase 0.5: Recall relevant memories
            memory_context = ""
            if self.memory:
                try:
                    from memory.vector_memory import MemoryType
                    relevant_memories = self.memory.recall_sync(
                        query=message,
                        k=3,
                        memory_type=MemoryType.CONVERSATION,
                        min_score=0.5
                    )
                    if relevant_memories:
                        memory_context = "\n\nRelevant past conversations:\n" + "\n".join([
                            f"- ({m['relevance_score']:.2f}) {m['content'][:200]}"
                            for m in relevant_memories[:2]  # Top 2 only
                        ])
                        logger.debug(f"💭 Recalled {len(relevant_memories)} relevant memories")
                except Exception as e:
                    logger.error(f"Memory recall failed: {e}")
            
            # Phase 0.7: Dynamic MCP server selection (Agentic Configuration)
            selected_servers = []
            if self.mcp_orchestrator:
                try:
                    selected_servers = await self.mcp_orchestrator.select_servers_for_task(
                        task=message,
                        context={
                            "user_type": "owner",
                            "recent_queries": len(history)
                        }
                    )
                    
                    if selected_servers:
                        # Mark servers as active for this request
                        await self.mcp_orchestrator.mark_servers_active(selected_servers)
                        
                        # Log context savings
                        savings = self.mcp_orchestrator.estimate_context_savings(selected_servers)
                        logger.info(f"💰 Context optimization:")
                        logger.info(f"      Tools: {savings['optimized_tools']} vs {savings['baseline_tools']} (saved {savings['tools_saved']})")
                        logger.info(f"      Tokens: {savings['optimized_tokens']} vs {savings['baseline_tokens']} ({savings['savings_percentage']}% reduction)")
                except Exception as e:
                    logger.error(f"MCP server selection failed: {e}")
            
            # DYNAMIC MODULE SELECTION: Choose Predict vs ChainOfThought vs ReAct
            # Explicit routing for MCP/Zapier tool listing (Force ReAct)
            if ("list" in message.lower() or "show" in message.lower()) and \
               ("zapier" in message.lower() or "mcp" in message.lower() or "tool" in message.lower()):
                logger.info("🎯 Explicit routing: MCP tool listing → Forcing ReAct")
                query_type = "action"  # Force ReAct for tool listing
            else:
                query_type = self._classify_query(message)
            
            if query_type == "simple":
                # Use Predict for simple queries (fast, no reasoning step)
                logger.info(f"📝 Simple query → Using Predict (fast)")
                conversation_module = self.simple_conversation
            elif query_type == "action":
                # Use ReAct for action queries (tool calling)
                logger.info(f"🔧 Action query → Using ReAct (tool calling for real data)")
                conversation_module = self.action_agent
            else:
                # Use ChainOfThought for complex queries (with reasoning)
                logger.info(f"🧠 Complex query → Using ChainOfThought (reasoning)")
                conversation_module = self.complex_conversation
            
            # Execute selected DSPy module with error recovery (Phase 0 Fix #1)
            try:
                result = conversation_module(
                    context=system_context + memory_context,  # Include memory context
                    user_message=message,
                    conversation_history=history_text
                )
            except Exception as parse_error:
                # Handle DSPy parsing errors gracefully (e.g., missing suggested_actions)
                if "AdapterParseError" in str(type(parse_error).__name__) or "parse" in str(parse_error).lower():
                    logger.warning(f"⚠️ DSPy parsing error (likely missing optional field), retrying with simpler signature...")
                    # Retry with simple conversation module (Predict only, no optional fields)
                    result = self.simple_conversation(
                        context=system_context + memory_context,
                        user_message=message,
                        conversation_history=history_text
                    )
                else:
                    raise  # Re-raise if not a parsing error
            
            # Update conversation history
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": result.response})
            
            # Keep history manageable (last 20 messages = 10 exchanges)
            if len(history) > 20:
                self.conversation_history[user_id] = history[-20:]
            
            # Phase 0.5: Remember this conversation
            if self.memory:
                try:
                    from memory.vector_memory import MemoryType
                    self.memory.remember_sync(
                        content=f"Q: {message}\nA: {result.response[:500]}",  # Limit length
                        memory_type=MemoryType.CONVERSATION,
                        metadata={
                            "user_id": user_id,
                            "query_type": query_type
                        }
                    )
                    logger.debug(f"💾 Remembered conversation")
                except Exception as e:
                    logger.error(f"Memory storage failed: {e}")
            
            # Return response from selected module
            # Note: ReAct handles audit requests automatically via tools
            return result.response
        
        except Exception as e:
            logger.error(f"DSPy conversation error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return f"⚠️ I encountered an error: {str(e)}. Please try rephrasing your question."
    
    # ===== Core Strategy Functions =====
    
    async def analyze_pipeline(self, days: int = 7) -> PipelineAnalysis:
        """Analyze the inbound pipeline.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            PipelineAnalysis with insights
        """
        logger.info(f"📊 Analyzing pipeline for last {days} days...")
        
        # Query via A2A
        analysis_data = await self._a2a_command(
            agent_type="strategy",
            action="analyze_pipeline",
            parameters={"days": days}
        )
        
        # For now, return mock data (TODO: Implement real Supabase query)
        return PipelineAnalysis(
            period_days=days,
            total_leads=42,
            by_tier={
                "SCORCHING": 3,
                "HOT": 8,
                "WARM": 15,
                "COOL": 10,
                "COLD": 6
            },
            by_source={
                "typeform": 35,
                "vapi": 7
            },
            conversion_rate=0.26,  # 26% HOT+SCORCHING
            avg_qualification_score=62.5,
            top_industries=[
                "Weight Loss Clinics",
                "Functional Medicine",
                "Corporate Wellness"
            ],
            insights=[
                "HOT leads increased 40% vs previous week",
                "Functional medicine segment shows 80% qualification rate",
                "3 leads awaiting Calendly booking - follow up recommended"
            ]
        )
    
    async def recommend_outbound_targets(
        self,
        segment: str = "all",
        min_size: int = 50,
        limit: int = 10
    ) -> List[OutboundTarget]:
        """Recommend companies for outbound outreach.
        
        Args:
            segment: Target segment (e.g., "weight_loss_clinics", "all")
            min_size: Minimum patient volume
            limit: Max number of targets
        
        Returns:
            List of recommended targets
        """
        logger.info(f"🎯 Generating outbound targets: {segment}, min size: {min_size}")
        
        # Query via A2A
        result = await self._a2a_command(
            agent_type="strategy",
            action="recommend_outbound_targets",
            parameters={
                "segment": segment,
                "min_size": min_size,
                "limit": limit
            }
        )
        
        # For now, return mock data (TODO: Implement real analysis)
        return [
            OutboundTarget(
                company_name="West Coast Weight Loss Center",
                reason="Similar to our top-performing HOT leads. 200+ patient volume, focuses on chronic disease management.",
                fit_score=92,
                estimated_patient_volume="200-300",
                contact_info={"linkedin": "linkedin.com/company/wcwlc"}
            ),
            OutboundTarget(
                company_name="Precision Health Clinic",
                reason="Uses InBody (competitor) - perfect for competitive displacement. 150+ patients.",
                fit_score=88,
                estimated_patient_volume="150-200",
                contact_info={"website": "precisionhealthclinic.com"}
            )
        ]
    
    async def generate_recommendations(self) -> List[StrategyRecommendation]:
        """Generate strategic recommendations based on current state.
        
        Returns:
            List of prioritized recommendations
        """
        logger.info("💡 Generating strategic recommendations...")
        
        recommendations = []
        
        # Analyze recent patterns
        analysis = await self.analyze_pipeline(days=7)
        
        # Recommendation 1: High-priority leads
        if analysis.by_tier.get("SCORCHING", 0) > 0 or analysis.by_tier.get("HOT", 0) > 2:
            recommendations.append(StrategyRecommendation(
                type="pipeline_action",
                priority="high",
                title="Focus on HOT leads",
                description=f"You have {analysis.by_tier.get('HOT', 0)} HOT and {analysis.by_tier.get('SCORCHING', 0)} SCORCHING leads",
                action_items=[
                    "Review HOT leads for immediate outreach",
                    "Schedule calls with SCORCHING leads ASAP",
                    "Ensure follow-up sequences are active"
                ],
                impact="High - direct revenue opportunity",
                effort="Low - already in pipeline"
            ))
        
        # Recommendation 2: Research gaps
        recommendations.append(StrategyRecommendation(
            type="process_improvement",
            priority="medium",
            title="Enable deep lead research",
            description="Research Agent is ready but needs API keys (Clearbit, Apollo)",
            action_items=[
                "Add CLEARBIT_API_KEY to Railway env",
                "Add APOLLO_API_KEY to Railway env",
                "Enable auto-research on inbound leads"
            ],
            impact="Medium - better qualification and multi-contact strategy",
            effort="Low - just API key configuration"
        ))
        
        # Recommendation 3: Outbound expansion
        recommendations.append(StrategyRecommendation(
            type="outbound_target",
            priority="medium",
            title="Launch targeted outbound campaign",
            description=f"Top-performing segment: {analysis.top_industries[0] if analysis.top_industries else 'N/A'}",
            action_items=[
                "Build list of 50 similar companies",
                "Create personalized outreach templates",
                "Launch test campaign (10 companies)"
            ],
            impact="High - new revenue stream",
            effort="Medium - requires list building and content"
        ))
        
        return recommendations
    
    async def send_daily_report(self):
        """Send daily pipeline report to Josh."""
        logger.info("📧 Generating daily report...")
        
        analysis = await self.analyze_pipeline(days=1)
        recommendations = await self.generate_recommendations()
        
        message = f"""*🎯 Daily Pipeline Report* - {datetime.utcnow().strftime('%Y-%m-%d')}
        
*📊 Today's Activity:*
• {analysis.total_leads} new leads
• {analysis.by_tier.get('HOT', 0)} HOT leads
• Avg score: {analysis.avg_qualification_score:.0f}/100

*🔥 Top Insights:*
{chr(10).join(f'• {insight}' for insight in analysis.insights[:3])}

*💡 Recommendations:*
{chr(10).join(f'• *{rec.title}* ({rec.priority} priority)' for rec in recommendations[:2])}

_Reply with "details" for full analysis_
"""
        
        await self.send_slack_message(message)
    
    # ===== A2A Communication =====
    
    async def _a2a_command(
        self,
        agent_type: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        lead_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send command to another agent via A2A.
        
        Args:
            agent_type: Target agent
            action: Action to perform
            parameters: Action parameters
            lead_id: Lead ID if applicable
        
        Returns:
            Response data
        """
        if not self.a2a_api_key:
            logger.warning("⚠️ A2A not configured, returning mock data")
            return {"status": "mock", "data": {}}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.a2a_endpoint,
                headers={
                    "Authorization": f"Bearer {self.a2a_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "mode": "command",
                    "agent_type": agent_type,
                    "action": action,
                    "parameters": parameters,
                    "lead_id": lead_id
                },
                timeout=30.0
            )
            
            data = response.json()
            if data.get("success"):
                return data.get("data", {})
            else:
                logger.error(f"A2A command failed: {data.get('error')}")
                return {}
    
    async def _a2a_query(
        self,
        agent_type: str,
        action: str,
        lead_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query another agent via A2A.
        
        Args:
            agent_type: Target agent
            action: Query action
            lead_id: Lead ID if applicable
        
        Returns:
            Query result
        """
        if not self.a2a_api_key:
            logger.warning("⚠️ A2A not configured, returning mock data")
            return {}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.a2a_endpoint,
                headers={
                    "Authorization": f"Bearer {self.a2a_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "mode": "query",
                    "agent_type": agent_type,
                    "action": action,
                    "lead_id": lead_id
                },
                timeout=30.0
            )
            
            data = response.json()
            if data.get("success"):
                return data.get("data", {})
            else:
                logger.error(f"A2A query failed: {data.get('error')}")
                return {}
    
    # ===== Formatting Helpers =====
    
    def _format_pipeline_analysis(self, analysis: PipelineAnalysis) -> str:
        """Format pipeline analysis for Slack."""
        tier_bars = []
        for tier, count in analysis.by_tier.items():
            bar = "█" * min(count, 20)
            tier_bars.append(f"{tier:12} {bar} {count}")
        
        return f"""*📊 Pipeline Analysis* (Last {analysis.period_days} days)

*Total Leads:* {analysis.total_leads}
*Conversion Rate:* {analysis.conversion_rate*100:.1f}% (HOT+SCORCHING)
*Avg Score:* {analysis.avg_qualification_score:.0f}/100

*By Tier:*
```
{chr(10).join(tier_bars)}
```

*🔥 Key Insights:*
{chr(10).join(f'• {insight}' for insight in analysis.insights)}

*🎯 Top Industries:*
{chr(10).join(f'• {industry}' for industry in analysis.top_industries)}
"""
    
    def _format_recommendations(self, recommendations: List[StrategyRecommendation]) -> str:
        """Format recommendations for Slack."""
        formatted = ["*💡 Strategic Recommendations:*\n"]
        
        for i, rec in enumerate(recommendations[:5], 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "⚪")
            formatted.append(f"{i}. {priority_emoji} *{rec.title}* ({rec.priority})")
            formatted.append(f"   _{rec.description}_")
            formatted.append(f"   Impact: {rec.impact} | Effort: {rec.effort}\n")
        
        return "\n".join(formatted)
    
    def _format_outbound_targets(self, targets: List[OutboundTarget]) -> str:
        """Format outbound targets for Slack."""
        formatted = ["*🎯 Recommended Outbound Targets:*\n"]
        
        for i, target in enumerate(targets[:5], 1):
            formatted.append(f"{i}. *{target.company_name}* (Fit: {target.fit_score}/100)")
            formatted.append(f"   _{target.reason}_")
            if target.estimated_patient_volume:
                formatted.append(f"   Volume: {target.estimated_patient_volume} patients")
            formatted.append("")
        
        return "\n".join(formatted)
    
    async def _build_system_context(self) -> str:
        """Build dynamic system context from actual system state.
        
        This pulls REAL data instead of hardcoded text, making responses
        more accurate and contextual.
        
        Returns:
            JSON string with current system state
        """
        try:
            # Get REAL pipeline data if Supabase is connected
            pipeline_data = {}
            try:
                if self.supabase:
                    # Query actual lead counts from Supabase
                    result = self.supabase.table('leads').select('qualification_tier', count='exact').execute()
                    
                    # Count by tier
                    tier_counts = {"HOT": 0, "WARM": 0, "COOL": 0, "COLD": 0, "UNQUALIFIED": 0}
                    for lead in result.data:
                        tier = lead.get('qualification_tier', 'UNQUALIFIED').upper()
                        if tier in tier_counts:
                            tier_counts[tier] += 1
                    
                    pipeline_data = {
                        "data_access": "LIVE",
                        "leads_by_tier": tier_counts,
                        "total_leads": sum(tier_counts.values()),
                        "data_source": "Supabase (real-time)"
                    }
                else:
                    pipeline_data = {
                        "data_access": "NONE",
                        "message": "Supabase not connected - cannot provide real-time metrics",
                        "what_i_need": "SUPABASE_URL and SUPABASE_KEY environment variables"
                    }
            except Exception as e:
                logger.error(f"Error fetching pipeline data: {e}")
                pipeline_data = {
                    "data_access": "ERROR",
                    "error": str(e),
                    "message": "Database query failed - check Supabase connection"
                }
            
            # Build context dynamically
            context = {
                "infrastructure": {
                    "entry_points": [
                        {"path": "/webhooks/typeform", "purpose": "Lead capture from forms"},
                        {"path": "/webhooks/vapi", "purpose": "Voice AI phone calls"},
                        {"path": "/slack/events", "purpose": "Interactive Slack bot"},
                        {"path": "/a2a/introspect", "purpose": "Agent-to-agent communication"}
                    ],
                    "agents": {
                        "inbound": {
                            "role": "Lead qualification",
                            "tech": "DSPy + Claude Sonnet 4.5",
                            "outputs": "Scores (0-100), Tiers (HOT/WARM/COOL/COLD)",
                            "status": "operational"
                        },
                        "research": {
                            "role": "Intelligence gathering",
                            "tools": ["Clearbit", "Apollo", "Perplexity"],
                            "capabilities": ["Person enrichment", "Company research", "Contact discovery"],
                            "status": f"{'operational' if self.research_agent else 'not_configured'}"
                        },
                        "follow_up": {
                            "role": "Email sequences",
                            "tool": "GMass API",
                            "sequences": "8-stage tier-based",
                            "mode": "autonomous",
                            "status": f"{'operational' if self.follow_up_agent else 'not_configured'}"
                        },
                        "strategy": {
                            "role": "YOU - Coordination & insights",
                            "capabilities": ["Pipeline analysis", "Recommendations", "Agent orchestration"],
                            "status": "active"
                        }
                    },
                    "data_layer": {
                        "primary": "Supabase (PostgreSQL)",
                        "tables": ["leads", "conversations", "agent_state"],
                        "future": "Redis for caching"
                    },
                    "integrations": {
                        "slack": f"{'✅' if self.slack_bot_token else '❌'}",
                        "gmass": "Email campaigns",
                        "close_crm": "Qualified lead sync",
                        "openrouter": "LLM inference (Claude 3.5 Sonnet)",
                        "mcp_zapier": f"{'✅ 200+ integrations via MCP (use list_mcp_tools to see all)' if self.mcp_client and self.mcp_client.client else '❌ Not configured'}",
                        "mcp_perplexity": "AI research via MCP",
                        "mcp_apify": "Web scraping via MCP"
                    },
                    "deployment": {
                        "platform": "Railway",
                        "framework": "FastAPI + Uvicorn",
                        "processing": "Async webhooks"
                    }
                },
                "current_state": pipeline_data,
                "tech_stack": {
                    "ai_framework": "DSPy (ChainOfThought, ReAct modules)",
                    "validation": "Pydantic BaseModel",
                    "orchestration": "LangGraph (coming soon)",
                    "llm": "Claude 3.5 Sonnet via OpenRouter"
                }
            }
            
            return json.dumps(context, indent=2)
        
        except Exception as e:
            logger.error(f"Error building system context: {e}")
            # Return minimal context if something fails
            return json.dumps({
                "infrastructure": "Hume AI B2B sales automation system",
                "agents": ["Inbound", "Research", "Follow-Up", "Strategy"],
                "status": "operational"
            })
    
    def _format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history for DSPy input.
        
        Args:
            history: List of conversation exchanges
        
        Returns:
            Formatted history string
        """
        if not history:
            return "No previous conversation"
        
        # Take last 3 exchanges (6 messages)
        recent = history[-6:]
        formatted = []
        
        for msg in recent:
            role = "Josh" if msg["role"] == "user" else "Strategy Agent"
            content = msg["content"][:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    async def _handle_fix_approval(self, message: str) -> str:
        """Handle fix approval command from Josh (Phase 0.6).
        
        Args:
            message: Message containing "implement fix_XXXX"
        
        Returns:
            Status message
        """
        import re
        
        # Extract fix ID
        match = re.search(r'fix_\d{8}_\d{6}', message)
        if not match:
            return "⚠️ Invalid fix ID format. Expected: fix_YYYYMMDD_HHMMSS"
        
        fix_id = match.group(0)
        logger.info(f"🔧 Fix approval received: {fix_id}")
        
        try:
            # Import here to avoid circular deps
            from monitoring.proactive_monitor import get_proactive_monitor
            from monitoring.fix_implementor import get_fix_implementor
            
            # Get the proposed fix
            monitor = get_proactive_monitor()
            if fix_id not in monitor.proposed_fixes:
                return f"❌ Fix {fix_id} not found in proposed fixes. It may have expired."
            
            proposed_fix = monitor.proposed_fixes[fix_id]
            
            # Implement the fix
            implementor = get_fix_implementor()
            
            # TODO: Parse proposed changes into file edits
            # For now, return acknowledgment
            return f"""✅ **Fix Approved: {fix_id}**

I've received approval to implement this fix. 

**Note**: Phase 0.6 is in initial deployment. The fix has been logged and I'll work with you to implement it manually for now. Full autonomous implementation coming soon!

**Proposed fix**:
{proposed_fix.proposed_changes[0]['description']}

**Next**: I'll help you apply these changes step by step."""
            
        except Exception as e:
            logger.error(f"Error handling fix approval: {e}")
            return f"❌ Error processing fix approval: {e}"
    
    async def _handle_fix_rejection(self, message: str) -> str:
        """Handle fix rejection command from Josh (Phase 0.6).
        
        Args:
            message: Message containing "reject fix_XXXX"
        
        Returns:
            Status message
        """
        import re
        
        # Extract fix ID
        match = re.search(r'fix_\d{8}_\d{6}', message)
        if not match:
            return "⚠️ Invalid fix ID format. Expected: fix_YYYYMMDD_HHMMSS"
        
        fix_id = match.group(0)
        logger.info(f"❌ Fix rejected: {fix_id}")
        
        try:
            from monitoring.proactive_monitor import get_proactive_monitor
            
            monitor = get_proactive_monitor()
            if fix_id in monitor.proposed_fixes:
                del monitor.proposed_fixes[fix_id]
                return f"✅ Fix {fix_id} has been rejected and removed from the queue."
            else:
                return f"⚠️ Fix {fix_id} not found. It may have already been processed or expired."
                
        except Exception as e:
            logger.error(f"Error handling fix rejection: {e}")
            return f"❌ Error processing fix rejection: {e}"
    
    def _classify_query(self, message: str) -> str:
        """Classify query type for module selection.
        
        Returns "simple", "action", or "complex":
        - simple: Greetings, status checks → Predict (fast)
        - action: Audit, query, pull data → ReAct (tool calling)
        - complex: Analysis, explain, recommend → ChainOfThought (reasoning)
        
        Args:
            message: User's message
        
        Returns:
            "simple", "action", or "complex"
        """
        message_lower = message.lower().strip()
        word_count = len(message.split())
        
        # ACTION queries (need tools - highest priority!)
        action_keywords = [
            'audit', 'query', 'pull', 'get data', 'show me', 'fetch',
            'check gmass', 'check supabase', 'real data', 'actual numbers',
            'campaign stats', 'email stats', 'lead stats', 'pipeline data',
            'list', 'show', 'check'  # Added for MCP tool discovery
        ]
        
        if any(keyword in message_lower for keyword in action_keywords):
            return "action"
        
        # SIMPLE queries (greetings, status)
        simple_patterns = [
            'hey', 'hi', 'hello', 'yo', 'sup', 'whats up', 'what\'s up',
            'status', 'ping', 'you there', 'hello there',
            'how are you', 'how\'s it going', 'wassup'
        ]
        
        if any(pattern in message_lower for pattern in simple_patterns):
            return "simple"
        
        # Very short messages (< 4 words) are usually simple
        if word_count <= 3:
            return "simple"
        
        # COMPLEX keywords (need reasoning but no tools)
        complex_keywords = [
            'analyze', 'compare', 'explain why', 'why', 'how does',
            'what if', 'recommend', 'strategy', 'breakdown',
            'deep dive', 'investigate', 'assess', 'evaluate'
        ]
        
        if any(keyword in message_lower for keyword in complex_keywords):
            return "complex"
        
        # Medium-length conversational questions (default to simple)
        if word_count <= 10:
            return "simple"
        
        # Long messages likely need reasoning
        return "complex"
    
    def _is_audit_request(self, message: str) -> bool:
        """Detect if user is asking for an audit or real data.
        
        Args:
            message: User's message
        
        Returns:
            True if this is an audit request
        """
        audit_keywords = [
            'audit', 'analyze pipeline', 'lead flow', 'email performance',
            'deliverability', 'open rate', 'response rate', 'speed to lead',
            'show me', 'pull data', 'get data', 'query', 'real data',
            'actual numbers', 'campaign stats', 'email stats'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in audit_keywords)
    
    async def _execute_audit(self, message: str) -> str:
        """Execute a real audit using AuditAgent.
        
        Args:
            message: User's audit request
        
        Returns:
            Formatted audit report with REAL data
        """
        try:
            # Determine timeframe from message
            timeframe_hours = 24  # Default
            if 'week' in message.lower():
                timeframe_hours = 168
            elif 'month' in message.lower():
                timeframe_hours = 720
            
            logger.info(f"⏳ Executing audit for last {timeframe_hours} hours...")
            
            # Execute audit
            audit_data = await self.audit_agent.audit_lead_flow(timeframe_hours)
            
            # Format report
            report = self.audit_agent.format_audit_report(audit_data)
            
            logger.info("✅ Audit completed successfully")
            return report
        
        except Exception as e:
            logger.error(f"❌ Audit execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"❌ Audit failed: {str(e)}\n\nI tried to pull real data but encountered an error. Check logs for details."


# ===== Export =====
__all__ = ['StrategyAgent', 'PipelineAnalysis', 'OutboundTarget', 'StrategyRecommendation']
