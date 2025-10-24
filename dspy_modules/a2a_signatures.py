"""
Agent-to-Agent (A2A) Communication Signatures

DSPy-native signatures for inter-agent communication.
Inspired by Microsoft AutoGen's Agent-as-Tool pattern.

Enables:
- Type-safe agent communication
- Optimizable A2A protocols
- Structured requests/responses
- Better error handling
"""

import dspy
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


# ===== PYDANTIC MODELS FOR A2A COMMUNICATION =====

class A2ARequest(BaseModel):
    """Structured request from one agent to another."""
    from_agent: str = Field(..., description="Name of requesting agent")
    to_agent: str = Field(..., description="Name of target agent")
    request_type: str = Field(..., description="query, delegate, notify")
    message: str = Field(..., description="Request message")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    priority: str = Field(default="medium", description="urgent, high, medium, low")


class A2AResponse(BaseModel):
    """Structured response from agent."""
    from_agent: str = Field(..., description="Name of responding agent")
    to_agent: str = Field(..., description="Name of requesting agent")
    success: bool = Field(..., description="Request completed successfully?")
    response: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured data")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ===== DSPY SIGNATURES FOR A2A COMMUNICATION =====

class AgentToolCall(dspy.Signature):
    """Universal agent-as-tool signature (AutoGen-inspired).
    
    Enables any agent to call any other agent as a tool.
    Provides type-safe, optimizable inter-agent communication.
    """
    agent_name: str = dspy.InputField(desc="Which agent to call (InboundAgent, ResearchAgent, etc.)")
    task: str = dspy.InputField(desc="Task to delegate to the agent")
    context: str = dspy.InputField(desc="Additional context (JSON string)")
    
    result: str = dspy.OutputField(desc="Agent's response")
    data: str = dspy.OutputField(desc="Structured data (JSON string)")
    success: bool = dspy.OutputField(desc="Task completed successfully?")


class AskInboundAgent(dspy.Signature):
    """Ask InboundAgent about lead qualification and pipeline.
    
    Use this when you need:
    - Pipeline statistics (HOT/WARM/COOL/COLD counts)
    - Lead qualification status
    - Qualification criteria
    - Lead tier information
    """
    question: str = dspy.InputField(desc="Question about leads or qualification")
    lead_id: Optional[str] = dspy.InputField(desc="Specific lead ID (optional)")
    
    response: str = dspy.OutputField(desc="InboundAgent's answer")
    pipeline_data: Optional[Dict] = dspy.OutputField(desc="Pipeline statistics if requested")
    lead_data: Optional[Dict] = dspy.OutputField(desc="Lead data if requested")


class AskResearchAgent(dspy.Signature):
    """Ask ResearchAgent for intelligence gathering.
    
    Use this when you need:
    - Company research
    - Person research
    - Competitive intelligence
    - Market analysis
    """
    research_request: str = dspy.InputField(desc="What to research")
    lead_context: str = dspy.InputField(desc="Lead/company context (JSON)")
    depth: str = dspy.InputField(desc="quick, standard, deep")
    
    findings: str = dspy.OutputField(desc="Research findings summary")
    sources: List[str] = dspy.OutputField(desc="Data sources used")
    confidence: float = dspy.OutputField(desc="Confidence score 0-1")


class AskFollowUpAgent(dspy.Signature):
    """Ask FollowUpAgent about email sequences and follow-up status.
    
    Use this when you need:
    - Follow-up sequence status
    - Email delivery status
    - Next scheduled action
    - Engagement metrics
    """
    query: str = dspy.InputField(desc="Question about follow-ups")
    lead_id: Optional[str] = dspy.InputField(desc="Specific lead ID (optional)")
    
    status: str = dspy.OutputField(desc="Follow-up status")
    next_action: str = dspy.OutputField(desc="Next scheduled action")
    emails_sent: int = dspy.OutputField(desc="Number of emails sent")


class AskAuditAgent(dspy.Signature):
    """Ask AuditAgent for analytics and metrics.
    
    Use this when you need:
    - Campaign performance
    - Conversion metrics
    - Cost analysis
    - ROI calculations
    """
    query: str = dspy.InputField(desc="Analytics question")
    time_range: str = dspy.InputField(desc="24h, 7d, 30d, all")
    
    metrics: Dict = dspy.OutputField(desc="Requested metrics")
    insights: str = dspy.OutputField(desc="Key insights")
    recommendations: str = dspy.OutputField(desc="Recommended actions")


class DelegateTask(dspy.Signature):
    """Delegate task to another agent with tracking.
    
    Use this for:
    - Complex tasks requiring specialist
    - Long-running research
    - Multi-step workflows
    """
    task_description: str = dspy.InputField(desc="Detailed task description")
    target_agent: str = dspy.InputField(desc="Which agent to delegate to")
    priority: str = dspy.InputField(desc="urgent, high, medium, low")
    deadline: Optional[str] = dspy.InputField(desc="Expected completion time")
    
    acceptance: bool = dspy.OutputField(desc="Agent accepted task?")
    estimated_time: str = dspy.OutputField(desc="Estimated completion time")
    task_id: str = dspy.OutputField(desc="Task tracking ID")


class NotifyAgent(dspy.Signature):
    """Send notification to another agent (no response expected).
    
    Use this for:
    - Status updates
    - Alerts
    - Information sharing
    """
    target_agent: str = dspy.InputField(desc="Agent to notify")
    notification: str = dspy.InputField(desc="Notification message")
    notification_type: str = dspy.InputField(desc="info, warning, error, success")
    
    delivered: bool = dspy.OutputField(desc="Notification delivered?")


# ===== AGENT CAPABILITY SIGNATURES =====

class DescribeCapabilities(dspy.Signature):
    """Ask agent to describe its capabilities.
    
    Used for:
    - Agent discovery
    - Capability matching
    - Task routing
    """
    agent_name: str = dspy.InputField(desc="Which agent to query")
    
    capabilities: List[str] = dspy.OutputField(desc="List of capabilities")
    tools: List[str] = dspy.OutputField(desc="Available tools")
    specialization: str = dspy.OutputField(desc="Agent's specialization")


class RouteTask(dspy.Signature):
    """Determine which agent should handle a task.
    
    Use this for:
    - Intelligent task routing
    - Load balancing
    - Capability matching
    """
    task: str = dspy.InputField(desc="Task description")
    available_agents: List[str] = dspy.InputField(desc="List of available agents")
    
    selected_agent: str = dspy.OutputField(desc="Best agent for this task")
    reasoning: str = dspy.OutputField(desc="Why this agent was selected")
    confidence: float = dspy.OutputField(desc="Confidence in selection 0-1")

