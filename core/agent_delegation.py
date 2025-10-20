"""
Agent Delegation Framework - Agent Zero Style

Enables agents to:
1. Create specialized subordinate agents dynamically
2. Delegate complex subtasks to subordinates
3. Maintain subordinate context and memory
4. Reset subordinates when needed

Based on Agent Zero's call_subordinate pattern.
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from agents.strategy_agent import StrategyAgent

logger = logging.getLogger(__name__)


class SubordinateAgent:
    """
    A subordinate agent spawned to handle a specific subtask.
    
    Subordinates are specialized, focused agents that inherit capabilities
    from their superior but have narrower context and goals.
    """
    
    def __init__(
        self,
        profile: str,
        superior_agent: Any,
        specialized_instructions: str
    ):
        """
        Initialize a subordinate agent.
        
        Args:
            profile: Role/specialization (e.g., "competitor_analyst", "market_researcher")
            superior_agent: The parent agent that spawned this subordinate
            specialized_instructions: Specific instructions for this subordinate's role
        """
        self.profile = profile
        self.superior = superior_agent
        self.specialized_instructions = specialized_instructions
        self.conversation_history: list = []
        self.data: Dict[str, Any] = {}
        
        # Set metadata
        self.data["_superior"] = superior_agent
        self.data["_profile"] = profile
        self.data["_created_at"] = asyncio.get_event_loop().time()
        
        logger.info(f"👶 Created subordinate: {profile}")
    
    def set_data(self, key: str, value: Any):
        """Store data in subordinate's memory."""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from subordinate's memory."""
        return self.data.get(key, default)
    
    async def process(self, message: str) -> str:
        """
        Process a message using the subordinate's specialized context.
        
        Args:
            message: Task or question for the subordinate
            
        Returns:
            Result from processing
        """
        # Build specialized context
        full_context = f"""
You are a specialized subordinate agent with the following role:

**Profile**: {self.profile}
**Specialized Instructions**: {self.specialized_instructions}

You were spawned by your superior agent to handle a specific subtask.
Focus ONLY on your specialized area. Be thorough and detailed.

Your superior's request: {message}
"""
        
        # Add conversation history
        if self.conversation_history:
            history_text = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in self.conversation_history[-5:]  # Last 5 messages
            ])
            full_context += f"\n\nPrevious conversation:\n{history_text}"
        
        # Use superior's DSPy module to process
        # (Subordinates use same LLM but with specialized context)
        try:
            # Use the superior's complex_conversation for reasoning
            result = await asyncio.to_thread(
                self.superior.complex_conversation,
                system_context=full_context,
                message=message,
                conversation_history=[]  # Subordinate has own history
            )
            
            response = result.response
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user",
                "content": message
            })
            self.conversation_history.append({
                "role": "assistant", 
                "content": response
            })
            
            logger.info(f"✅ Subordinate {self.profile} completed task")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Subordinate {self.profile} failed: {e}")
            return f"Error: {str(e)}"


class AgentDelegation:
    """
    Delegation manager for an agent.
    
    Allows agents to spawn and manage subordinate agents for complex tasks.
    Inspired by Agent Zero's call_subordinate pattern.
    """
    
    def __init__(self, parent_agent: Any):
        """
        Initialize delegation manager.
        
        Args:
            parent_agent: The agent that will use this delegation system
        """
        self.parent_agent = parent_agent
        self.subordinates: Dict[str, SubordinateAgent] = {}
        
        # Profile templates for common subordinate types
        self.profile_templates = {
            "competitor_analyst": """
                You are a competitive intelligence analyst.
                Your job is to deeply research specific competitors:
                - Products and pricing
                - Market positioning
                - Strengths and weaknesses
                - Customer segments
                - Marketing strategies
                
                Use MCP tools (Perplexity, web scraping) to gather data.
                Be thorough and cite sources.
            """,
            
            "market_researcher": """
                You are a market research specialist.
                Your job is to analyze markets and trends:
                - Market size and growth
                - Key players and dynamics
                - Customer segments and needs
                - Opportunities and threats
                - Industry trends
                
                Use MCP tools and databases to gather intelligence.
                Provide data-driven insights.
            """,
            
            "account_researcher": """
                You are an account-based marketing researcher.
                Your job is to deeply research specific target accounts:
                - Company profile and history
                - Decision makers and org chart
                - Technology stack
                - Pain points and needs
                - Recent news and events
                
                Use all available tools (Clearbit, Apollo, Perplexity, LinkedIn).
                Build a comprehensive account profile.
            """,
            
            "content_strategist": """
                You are a content marketing strategist.
                Your job is to plan and optimize content:
                - Audience analysis
                - Content ideation
                - Channel strategy
                - Messaging frameworks
                - Performance optimization
                
                Focus on personalized, high-converting content.
            """,
            
            "campaign_analyst": """
                You are a marketing campaign analyst.
                Your job is to analyze campaign performance:
                - Metrics and KPIs
                - A/B test results
                - Conversion funnels
                - ROI analysis
                - Optimization recommendations
                
                Use database tools to query real data.
                Provide actionable insights.
            """
        }
    
    async def call_subordinate(
        self,
        profile: str,
        message: str,
        reset: bool = False
    ) -> str:
        """
        Delegate a task to a specialized subordinate agent.
        
        This is the core delegation method inspired by Agent Zero.
        
        Args:
            profile: Subordinate role (e.g., "competitor_analyst")
            message: Task/question for the subordinate
            reset: Whether to create a fresh subordinate (clears history)
            
        Returns:
            Response from subordinate
            
        Example:
            result = await self.delegation.call_subordinate(
                profile="competitor_analyst",
                message="Analyze pricing strategy of Competitor X"
            )
        """
        logger.info(f"🎯 Delegating to subordinate: {profile}")
        logger.info(f"   Task: {message[:100]}...")
        
        # Get or create subordinate
        if profile not in self.subordinates or reset:
            # Get specialized instructions
            instructions = self.profile_templates.get(
                profile,
                f"You are a specialized {profile} subordinate agent."
            )
            
            # Create new subordinate
            subordinate = SubordinateAgent(
                profile=profile,
                superior_agent=self.parent_agent,
                specialized_instructions=instructions
            )
            
            # Store subordinate
            self.subordinates[profile] = subordinate
            
            if reset:
                logger.info(f"🔄 Reset subordinate: {profile}")
            else:
                logger.info(f"👶 Created new subordinate: {profile}")
        
        # Get subordinate
        subordinate = self.subordinates[profile]
        
        # Delegate task
        try:
            result = await subordinate.process(message)
            logger.info(f"✅ Subordinate {profile} completed task successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Subordinate {profile} failed: {e}")
            return f"Delegation failed: {str(e)}"
    
    def get_subordinate(self, profile: str) -> Optional[SubordinateAgent]:
        """Get a subordinate by profile."""
        return self.subordinates.get(profile)
    
    def list_subordinates(self) -> list[str]:
        """List all active subordinates."""
        return list(self.subordinates.keys())
    
    def remove_subordinate(self, profile: str):
        """Remove a subordinate (cleanup)."""
        if profile in self.subordinates:
            del self.subordinates[profile]
            logger.info(f"🗑️ Removed subordinate: {profile}")
    
    def clear_all_subordinates(self):
        """Clear all subordinates (cleanup)."""
        count = len(self.subordinates)
        self.subordinates.clear()
        logger.info(f"🗑️ Cleared {count} subordinates")


# ===== Convenience function for agents =====

def enable_delegation(agent: Any) -> AgentDelegation:
    """
    Enable delegation capabilities for an agent.
    
    Usage in agent __init__:
        from core.agent_delegation import enable_delegation
        self.delegation = enable_delegation(self)
    
    Then use:
        result = await self.delegation.call_subordinate("competitor_analyst", "...")
    """
    return AgentDelegation(agent)
