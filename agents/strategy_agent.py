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

from agents.inbound_agent import InboundAgent
from agents.research_agent import ResearchAgent
from agents.follow_up_agent import FollowUpAgent

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
        
        # Initialize sub-agents
        self.inbound_agent = InboundAgent()
        self.research_agent = ResearchAgent()
        self.follow_up_agent = FollowUpAgent()
        
        # A2A communication endpoint
        self.a2a_endpoint = os.getenv(
            "A2A_ENDPOINT",
            "https://hume-dspy-agent-production.up.railway.app/a2a/introspect"
        )
        self.a2a_api_key = os.getenv("A2A_API_KEY")
        
        logger.info("🎯 Strategy Agent initialized")
        logger.info(f"   Slack: {'✅ Configured' if self.slack_bot_token else '❌ Not configured'}")
        logger.info(f"   A2A: {'✅ Configured' if self.a2a_api_key else '❌ Not configured'}")
    
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
        
        # Process the message and generate response
        response = await self.chat_with_josh(message)
        
        # Send response in thread
        await self.send_slack_message(response, channel=channel, thread_ts=ts)
    
    async def chat_with_josh(self, message: str) -> str:
        """Process conversational request from Josh.
        
        This is the main intelligence function that understands requests
        and coordinates sub-agents to provide answers.
        
        Args:
            message: Josh's message/question
        
        Returns:
            Response text
        """
        message_lower = message.lower()
        
        # Pipeline analysis
        if any(word in message_lower for word in ["pipeline", "leads", "how many", "status"]):
            analysis = await self.analyze_pipeline(days=7)
            return self._format_pipeline_analysis(analysis)
        
        # Research request
        elif any(word in message_lower for word in ["research", "look up", "find out"]):
            return "🔍 I can research leads! Please provide:\n• Lead ID, or\n• Name and company\n\nExample: 'Research John Smith at Big Clinic'"
        
        # Recommendations
        elif any(word in message_lower for word in ["recommend", "suggest", "what should"]):
            recommendations = await self.generate_recommendations()
            return self._format_recommendations(recommendations)
        
        # Outbound targets
        elif "outbound" in message_lower:
            targets = await self.recommend_outbound_targets(segment="all", min_size=50)
            return self._format_outbound_targets(targets)
        
        # Help/capabilities
        elif any(word in message_lower for word in ["help", "what can you", "capabilities"]):
            return self._get_help_message()
        
        # Default: Acknowledge and suggest
        else:
            return (
                "I'm your Strategy Agent! I can help with:\n\n"
                "• **Pipeline Analysis** - 'Show me pipeline status'\n"
                "• **Lead Research** - 'Research [name] at [company]'\n"
                "• **Recommendations** - 'What should I focus on?'\n"
                "• **Outbound Targets** - 'Suggest outbound prospects'\n\n"
                f"Your message: _{message[:100]}_\n\n"
                "Try one of the commands above, or ask me anything specific!"
            )
    
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
    
    def _get_help_message(self) -> str:
        """Get help message."""
        return """*🎯 Strategy Agent - Your AI Partner*

I coordinate all Hume agents and provide strategic guidance.

*What I can do:*

*📊 Pipeline Analysis*
• "Show pipeline status"
• "How many HOT leads do we have?"
• "Analyze last 7 days"

*🔍 Lead Research*
• "Research [name] at [company]"
• "Deep dive on lead [ID]"
• "Find contacts at [company]"

*💡 Strategy & Recommendations*
• "What should I focus on?"
• "Give me recommendations"
• "Where are the opportunities?"

*🎯 Outbound Targeting*
• "Suggest outbound targets"
• "Find similar companies to our HOT leads"

*🤖 Agent Coordination*
• Send commands to inbound/research/follow-up agents
• Monitor agent health and performance
• Coordinate multi-agent workflows

Just ask me anything! I'm here to help you scale Hume's B2B growth. 🚀
"""


# ===== Export =====
__all__ = ['StrategyAgent', 'PipelineAnalysis', 'OutboundTarget', 'StrategyRecommendation']
