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
    suggested_actions: str = dspy.OutputField(desc="Comma-separated list of suggested next actions (optional)")


# ===== Strategy Agent =====

class StrategyAgent:
    """Personal AI advisor for strategic decision-making."""
    
    def __init__(self):
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
        
        # Return list of tools
        tools = [audit_lead_flow, query_supabase, get_pipeline_stats]
        logger.info(f"   Initialized {len(tools)} ReAct tools")
        return tools
    
    # ===== Slack Communication =====
    
    async def send_slack_message(
        self,
        message: str,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None
    ) -> Optional[str]:
        """Send message to Slack.
        
        Args:
            message: Message text
            channel: Channel ID (defaults to Josh's DM)
            thread_ts: Thread timestamp for replies
        
        Returns:
            Message timestamp (ts) or None
        """
        if not self.slack_bot_token:
            logger.warning("⚠️ Slack not configured, cannot send message")
            return None
        
        target_channel = channel or self.josh_slack_dm_channel
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {self.slack_bot_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": target_channel,
                    "text": message,
                    "thread_ts": thread_ts
                },
                timeout=10.0
            )
            
            data = response.json()
            if data.get("ok"):
                return data.get("ts")
            else:
                logger.error(f"Slack send failed: {data.get('error')}")
                return None
    
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
            # Build dynamic system context from actual system state
            system_context = await self._build_system_context()
            
            # Get conversation history for this user
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            history = self.conversation_history[user_id]
            history_text = self._format_conversation_history(history)
            
            # DYNAMIC MODULE SELECTION: Choose Predict vs ChainOfThought vs ReAct
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
            
            # Execute selected DSPy module
            result = conversation_module(
                context=system_context,  # Renamed to 'context' to match DSPy signature
                user_message=message,
                conversation_history=history_text
            )
            
            # Update conversation history
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": result.response})
            
            # Keep history manageable (last 20 messages = 10 exchanges)
            if len(history) > 20:
                self.conversation_history[user_id] = history[-20:]
            
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
                    result = self.supabase.table('leads').select('tier', count='exact').execute()
                    
                    # Count by tier
                    tier_counts = {"HOT": 0, "WARM": 0, "COOL": 0, "COLD": 0, "UNQUALIFIED": 0}
                    for lead in result.data:
                        tier = lead.get('tier', 'UNQUALIFIED')
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
                        "openrouter": "LLM inference (Claude 3.5 Sonnet)"
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
            'campaign stats', 'email stats', 'lead stats', 'pipeline data'
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
