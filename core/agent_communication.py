"""Inter-Agent Communication Framework

DSPy-native A2A communication with type safety and optimization.
Inspired by Microsoft AutoGen's Agent-as-Tool pattern.

Enables:
- Type-safe agent communication (Pydantic models)
- Optimizable A2A protocols (DSPy compilation)
- Structured requests/responses
- Better error handling
"""

import logging
import dspy
from typing import Any, Optional, Dict, List
import asyncio
from datetime import datetime
import httpx
import os

from dspy_modules.a2a_signatures import (
    AgentToolCall,
    AskInboundAgent,
    AskResearchAgent,
    AskFollowUpAgent,
    AskAuditAgent,
    DelegateTask,
    NotifyAgent,
    A2ARequest,
    A2AResponse
)
from models.pydantic_models import Lead, QualificationResult

logger = logging.getLogger(__name__)


class AgentMessage:
    """A message sent between agents."""

    def __init__(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
        message_type: str = "request",
        metadata: Optional[Dict] = None
    ):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.message = message
        self.message_type = message_type
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.id = f"{from_agent}→{to_agent}_{self.timestamp.timestamp()}"

    def __repr__(self):
        return f"AgentMessage({self.from_agent} → {self.to_agent}: {self.message[:50]}...)"


class CommunicationChannel:
    """Communication channel for inter-agent messages."""

    def __init__(self):
        self.messages: List[AgentMessage] = []
        self.max_history = 1000

    def send(self, message: AgentMessage):
        """Record a sent message."""
        self.messages.append(message)

        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

        logger.info(f"📨 {message.from_agent} → {message.to_agent}: {message.message[:80]}...")

    def get_conversation(self, agent1: str, agent2: str, limit: int = 10) -> List[AgentMessage]:
        """Get conversation between two agents."""
        conversation = [
            msg for msg in self.messages[-limit*2:]
            if (msg.from_agent == agent1 and msg.to_agent == agent2) or
               (msg.from_agent == agent2 and msg.to_agent == agent1)
        ]
        return conversation[-limit:]


# Global communication channel
_global_channel = CommunicationChannel()


# Agent name to A2A endpoint mapping
AGENT_A2A_ENDPOINTS = {
    "InboundAgent": "/agents/inbound/a2a",
    "ResearchAgent": "/agents/research/a2a",
    "FollowUpAgent": "/agents/followup/a2a",
    "StrategyAgent": "/a2a"
}


def _get_base_url() -> str:
    """Determine correct base URL for A2A communication."""
    # Check if running in Railway
    if os.getenv('RAILWAY_ENVIRONMENT'):
        return "http://localhost:8080"
    return "http://localhost:8000"


import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool for running sync DSPy calls in async context
_executor = ThreadPoolExecutor(max_workers=10)

class DSPyNativeA2A:
    """DSPy-native inter-agent communication with proper async handling."""

    def __init__(self, agent: Any):
        self.agent = agent
        self.agent_name = agent.__class__.__name__

        # DSPy modules for A2A communication
        self.agent_tool_call = dspy.ChainOfThought(AgentToolCall)
        self.ask_inbound = dspy.ChainOfThought(AskInboundAgent)
        self.ask_research = dspy.ChainOfThought(AskResearchAgent)
        self.ask_followup = dspy.ChainOfThought(AskFollowUpAgent)
        self.ask_audit = dspy.ChainOfThought(AskAuditAgent)
        self.delegate_task = dspy.ChainOfThought(DelegateTask)
        self.notify_agent = dspy.ChainOfThought(NotifyAgent)

    async def call_agent(
        self,
        target_agent_name: str,
        task: str,
        context: Optional[Dict] = None
    ) -> A2AResponse:
        """Call another agent using DSPy signatures (async-safe)."""
        import json

        # Run DSPy call in thread pool (DSPy is sync)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            self.agent_tool_call,
            target_agent_name,
            task,
            json.dumps(context or {})
        )

        # Return structured Pydantic response
        return A2AResponse(
            from_agent=self.agent_name,
            to_agent=target_agent_name,
            success=result.success,
            response=result.result,
            data=json.loads(result.data) if result.data else None
        )

# Keep existing HTTP-based A2A for backward compatibility
def _get_base_url() -> str:
    """
    Determine the correct base URL for A2A communication.
    
    In production (Railway), agents communicate via localhost since they're in the same container.
    The API_BASE_URL env var can override this if needed.
    """
    # Check for explicit override
    if base_url := os.getenv("API_BASE_URL"):
        return base_url
    
    # Check if we're in Railway (has RAILWAY_ENVIRONMENT env var)
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # In Railway, use localhost since all agents are in same container
        return "http://localhost:8080"  # Railway uses port 8080
    
    # Local development
    return "http://localhost:8000"


class AgentCommunication:
    """
    Inter-agent communication manager.
    
    Allows agents to ask each other for help, share information,
    and coordinate complex multi-agent tasks.
    """
    
    def __init__(self, agent: Any):
        """
        Initialize communication for an agent.
        
        Args:
            agent: The agent that will use this communication system
        """
        self.agent = agent
        self.agent_name = agent.__class__.__name__
        self.channel = _global_channel
        self.base_url = _get_base_url()
        
        logger.info(f"🔗 {self.agent_name} communication initialized (base_url: {self.base_url})")
    
    async def ask_agent(
        self,
        target_agent: Any,
        question: str,
        context: Optional[str] = None
    ) -> str:
        """
        Ask another agent for information or help.
        
        Args:
            target_agent: The agent to ask
            question: Question or request
            context: Optional context to provide
        
        Returns:
            Response from target agent
        
        Example:
            # Strategy Agent asks Research Agent
            research = await self.communication.ask_agent(
                target_agent=research_agent,
                question="What are the top 5 companies researched this week?"
            )
        """
        target_name = target_agent.__class__.__name__
        
        logger.info(f"🤝 {self.agent_name} asking {target_name}")
        logger.info(f"   Question: {question[:100]}...")
        
        # Build full message with context
        full_message = question
        if context:
            full_message = f"Context: {context}\n\nQuestion: {question}"
        
        # Record outgoing message
        outgoing = AgentMessage(
            from_agent=self.agent_name,
            to_agent=target_name,
            message=question,
            message_type="request"
        )
        self.channel.send(outgoing)
        
        try:
            # FIRST: Try A2A HTTP endpoint (new method)
            if target_name in AGENT_A2A_ENDPOINTS:
                endpoint = AGENT_A2A_ENDPOINTS[target_name]
                url = f"{self.base_url}{endpoint}"
                
                logger.info(f"🔗 Using A2A endpoint: {url}")
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        json={"message": full_message}
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    # Extract response text from A2A protocol response
                    if isinstance(result, dict) and "response" in result:
                        response_text = result["response"]
                    else:
                        response_text = str(result)
                    
                    # Record incoming response
                    incoming = AgentMessage(
                        from_agent=target_name,
                        to_agent=self.agent_name,
                        message=response_text,
                        message_type="response",
                        metadata={"in_response_to": outgoing.id, "via": "a2a_http"}
                    )
                    self.channel.send(incoming)
                    
                    logger.info(f"✅ {target_name} responded via A2A to {self.agent_name}")
                    return response_text
            
            # FALLBACK: Try legacy direct method calls
            logger.warning(f"⚠️ No A2A endpoint for {target_name}, trying legacy methods")
            
            # Call target agent's main method
            # Different agents have different interfaces, so we try common ones
            if hasattr(target_agent, 'process'):
                response = await target_agent.process(full_message)
            elif hasattr(target_agent, 'chat'):
                response = await target_agent.chat(full_message)
            elif hasattr(target_agent, 'handle_message'):
                response = await target_agent.handle_message(full_message)
            else:
                # Default: use DSPy module if available
                if hasattr(target_agent, 'simple_conversation'):
                    result = target_agent.simple_conversation(
                        message=full_message,
                        system_context="Answering question from another agent"
                    )
                    response = result.response
                else:
                    raise ValueError(f"Don't know how to communicate with {target_name}")
            
            # Record incoming response
            incoming = AgentMessage(
                from_agent=target_name,
                to_agent=self.agent_name,
                message=response,
                message_type="response",
                metadata={"in_response_to": outgoing.id, "via": "legacy_direct"}
            )
            self.channel.send(incoming)
            
            logger.info(f"✅ {target_name} responded to {self.agent_name}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to communicate with {target_name}: {e}")
            return f"Communication failed: {str(e)}"
    
    async def notify_agent(
        self,
        target_agent: Any,
        notification: str,
        metadata: Optional[Dict] = None
    ):
        """
        Send a notification to another agent (fire and forget).
        
        Args:
            target_agent: Agent to notify
            notification: Notification message
            metadata: Optional metadata
        
        Example:
            # Strategy Agent notifies Follow-Up Agent
            await self.communication.notify_agent(
                target_agent=followup_agent,
                notification="New high-priority lead qualified",
                metadata={"lead_id": lead.id}
            )
        """
        target_name = target_agent.__class__.__name__
        
        logger.info(f"📢 {self.agent_name} notifying {target_name}")
        logger.info(f"   Message: {notification[:100]}...")
        
        # Record notification
        message = AgentMessage(
            from_agent=self.agent_name,
            to_agent=target_name,
            message=notification,
            message_type="notification",
            metadata=metadata
        )
        self.channel.send(message)
    
    async def broadcast(
        self,
        agents: List[Any],
        message: str,
        wait_for_responses: bool = False
    ) -> Optional[List[str]]:
        """
        Broadcast a message to multiple agents.
        
        Args:
            agents: List of agents to broadcast to
            message: Message to broadcast
            wait_for_responses: Whether to wait for and collect responses
        
        Returns:
            List of responses if wait_for_responses=True, else None
        
        Example:
            # Strategy Agent broadcasts to all agents
            responses = await self.communication.broadcast(
                agents=[inbound_agent, research_agent, followup_agent],
                message="System maintenance in 5 minutes",
                wait_for_responses=False
            )
        """
        logger.info(f"📡 {self.agent_name} broadcasting to {len(agents)} agents")
        
        if wait_for_responses:
            # Ask all agents and wait for responses
            tasks = [
                self.ask_agent(agent, message)
                for agent in agents
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            return [
                resp if not isinstance(resp, Exception) else f"Error: {resp}"
                for resp in responses
            ]
        else:
            # Fire and forget notifications
            for agent in agents:
                await self.notify_agent(agent, message)
            return None
    
    def get_conversation_with(self, other_agent_name: str, limit: int = 10) -> List[AgentMessage]:
        """Get conversation history with another agent."""
        return self.channel.get_conversation(self.agent_name, other_agent_name, limit)
    
    def get_activity_log(self, limit: int = 20) -> List[AgentMessage]:
        """Get this agent's communication activity."""
        return self.channel.get_agent_activity(self.agent_name, limit)


# ===== Convenience functions =====

def enable_communication(agent: Any) -> AgentCommunication:
    """
    Enable communication capabilities for an agent.
    
    Usage in agent __init__:
        from core.agent_communication import enable_communication
        self.communication = enable_communication(self)
    
    Then use:
        response = await self.communication.ask_agent(other_agent, "question")
    """
    return AgentCommunication(agent)


def get_global_communication_channel() -> CommunicationChannel:
    """Get the global communication channel for monitoring."""
    return _global_channel


# ===== Static helper methods (for convenience) =====

async def ask_agent_static(from_agent: Any, to_agent: Any, question: str, context: Optional[str] = None) -> str:
    """
    Static helper to ask one agent from another without setting up communication first.
    
    Usage:
        from core.agent_communication import ask_agent_static
        
        result = await ask_agent_static(
            from_agent=self,
            to_agent=research_agent,
            question="What's the latest research?"
        )
    """
    comm = AgentCommunication(from_agent)
    return await comm.ask_agent(to_agent, question, context)

