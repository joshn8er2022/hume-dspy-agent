"""A2A Introspection API for agent-to-agent communication.

This module enables external agents (like Claude Code) to query the autonomous
agents about their internal state, reasoning, and decision-making processes.

Benefits:
- Proactive debugging without waiting for errors
- Recursive gap detection (agents reveal their own blockers)
- Real-time validation of agent decisions
- Transparent reasoning chain inspection
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from models import Lead, QualificationResult, LeadTier
from agents.follow_up_agent import FollowUpAgent, LeadJourneyState
from agents.inbound_agent import InboundAgent

logger = logging.getLogger(__name__)


# ===== Request/Response Models =====

class IntrospectionRequest(BaseModel):
    """Request format for A2A introspection queries."""
    agent_type: str = Field(..., description="Agent to query: 'follow_up' or 'qualification'")
    query_type: str = Field(..., description="Query type: 'show_state', 'explain_score', 'list_leads', 'test_qualification'")
    lead_id: Optional[str] = Field(None, description="Lead ID for state queries")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test lead data for validation")


class AgentState(BaseModel):
    """Current state of a lead in the follow-up agent."""
    lead_id: str
    tier: str
    status: str
    email_sent: bool
    follow_up_count: int
    next_follow_up_hours: int
    response_received: bool
    escalated: bool
    error: Optional[str]
    slack_thread_ts: Optional[str]
    current_node: Optional[str] = Field(None, description="Current graph node")
    next_node: Optional[str] = Field(None, description="Next scheduled node")


class QualificationBreakdown(BaseModel):
    """Detailed breakdown of qualification scoring."""
    total_score: int
    tier: str
    is_qualified: bool
    criteria: Dict[str, int] = Field(..., description="Score breakdown by criteria")
    reasoning: str
    key_factors: List[str]
    concerns: List[str]
    missing_fields: List[str] = Field(..., description="Fields that could improve score")
    processing_time_ms: int


class IntrospectionResponse(BaseModel):
    """Response from A2A introspection query."""
    success: bool
    query_type: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ===== Introspection Service =====

class AgentIntrospectionService:
    """Service for A2A introspection of autonomous agents."""

    def __init__(self):
        # Initialize DSPy before creating agents (base_model pattern)
        self._ensure_dspy_configured()

        self.follow_up_agent = FollowUpAgent()
        self.qualification_agent = InboundAgent()

    def _ensure_dspy_configured(self):
        """Ensure DSPy is configured with an LM (base_model pattern).

        This is the 'lm = base_model' fix your developer mentioned.

        DSPy's modular abstraction allows you to swap LMs by reassigning
        the base_model via dspy.configure(lm=base_model). This changes
        the underlying model for all subsequent calls without altering
        pipeline logic or data structures (Pydantic + LangGraph intact).

        This solves issues related to:
        - Model-specific bugs or compatibility
        - Missing LM initialization
        - Performance issues with specific models

        The key insight: DSPy decouples the LM from infrastructure,
        so switching models isolates whether issues are model-specific
        or elsewhere in the stack.
        """
        import dspy
        import os

        # Get API key (prioritize OpenRouter for Sonnet 4.5)
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        openai_api_key = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("OPENAI_KEY")
        )
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Create base_model instance - prioritize OpenRouter Sonnet 4.5
        if openrouter_api_key:
            base_model = dspy.LM('openrouter/anthropic/claude-sonnet-4.5', api_key=openrouter_api_key)
            logger.info("🔄 Switching to base_model: openrouter/anthropic/claude-sonnet-4.5")
        elif openai_api_key:
            base_model = dspy.LM('openai/gpt-4o', api_key=openai_api_key)
            logger.info("🔄 Switching to base_model: openai/gpt-4o (fallback)")
        elif anthropic_api_key:
            base_model = dspy.LM('anthropic/claude-3-5-sonnet-20241022', api_key=anthropic_api_key)
            logger.info("🔄 Switching to base_model: anthropic/claude-3-5-sonnet-20241022 (fallback)")
        else:
            raise ValueError("No LM API key found. Set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")

        # Swap the LM by reconfiguring with base_model
        # This decouples the LM from the rest of the infrastructure
        dspy.configure(lm=base_model)

        logger.info(f"✅ DSPy configured with base_model (Pydantic + LangGraph infrastructure intact)")

    def handle_query(self, request: IntrospectionRequest) -> IntrospectionResponse:
        """Route introspection query to appropriate handler."""
        try:
            if request.agent_type == "follow_up":
                data = self._handle_follow_up_query(request)
            elif request.agent_type == "qualification":
                data = self._handle_qualification_query(request)
            else:
                raise ValueError(f"Unknown agent type: {request.agent_type}")

            return IntrospectionResponse(
                success=True,
                query_type=request.query_type,
                data=data
            )

        except Exception as e:
            logger.error(f"Introspection error: {str(e)}")
            return IntrospectionResponse(
                success=False,
                query_type=request.query_type,
                error=str(e)
            )

    # ===== Follow-up Agent Introspection =====

    def _handle_follow_up_query(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle follow-up agent queries."""

        if request.query_type == "show_state":
            if not request.lead_id:
                raise ValueError("lead_id required for show_state query")
            return self._get_follow_up_state(request.lead_id)

        elif request.query_type == "list_leads":
            return self._list_active_leads()

        else:
            raise ValueError(f"Unknown follow-up query type: {request.query_type}")

    def _get_follow_up_state(self, lead_id: str) -> Dict[str, Any]:
        """Get current state of a lead in the follow-up agent."""
        config = {"configurable": {"thread_id": lead_id}}

        try:
            state = self.follow_up_agent.graph.get_state(config)

            if not state or not state.values:
                return {
                    "exists": False,
                    "message": f"No follow-up state found for lead {lead_id}"
                }

            # Extract current node from state metadata
            current_node = None
            next_node = None
            if hasattr(state, 'next') and state.next:
                next_node = state.next[0] if state.next else None

            state_data = AgentState(
                lead_id=state.values.get('lead_id'),
                tier=state.values.get('tier'),
                status=state.values.get('status'),
                email_sent=state.values.get('email_sent', False),
                follow_up_count=state.values.get('follow_up_count', 0),
                next_follow_up_hours=state.values.get('next_follow_up_hours', 0),
                response_received=state.values.get('response_received', False),
                escalated=state.values.get('escalated', False),
                error=state.values.get('error'),
                slack_thread_ts=state.values.get('slack_thread_ts'),
                current_node=current_node,
                next_node=next_node
            )

            return {
                "exists": True,
                "state": state_data.model_dump(),
                "graph_metadata": {
                    "checkpoint_id": state.config.get("configurable", {}).get("thread_id"),
                    "parent_checkpoint": getattr(state, 'parent_config', None)
                }
            }

        except Exception as e:
            logger.error(f"Error getting follow-up state: {str(e)}")
            return {
                "exists": False,
                "error": str(e)
            }

    def _list_active_leads(self) -> Dict[str, Any]:
        """List all leads currently in the follow-up system."""
        # Note: This would require iterating through stored checkpoints
        # For now, return a placeholder
        return {
            "message": "List active leads requires checkpoint enumeration (not implemented)",
            "suggestion": "Query specific lead_id using show_state instead"
        }

    # ===== Qualification Agent Introspection =====

    def _handle_qualification_query(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle qualification agent queries."""

        if request.query_type == "explain_score":
            if not request.lead_id and not request.test_data:
                raise ValueError("Either lead_id or test_data required for explain_score")
            return self._explain_qualification(request.lead_id, request.test_data)

        elif request.query_type == "test_qualification":
            if not request.test_data:
                raise ValueError("test_data required for test_qualification")
            return self._test_qualification(request.test_data)

        else:
            raise ValueError(f"Unknown qualification query type: {request.query_type}")

    def _explain_qualification(self, lead_id: Optional[str], test_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Explain qualification scoring for a lead."""

        # If test_data provided, create a test Lead object
        if test_data:
            from utils.typeform_transform import transform_typeform_webhook
            lead = transform_typeform_webhook(test_data)
        else:
            # Load lead from database
            from api.processors import supabase

            if not supabase:
                return {"error": "Supabase client not initialized"}

            lead_data = supabase.table('leads').select('*').eq('id', lead_id).single().execute()

            if not lead_data.data:
                return {"error": f"Lead {lead_id} not found"}

            lead = Lead(**lead_data.data)

        # Run qualification
        result: QualificationResult = self.qualification_agent.forward(lead)

        # Identify missing fields that could improve score
        missing_fields = []
        if not lead.get_field('business_size'):
            missing_fields.append("business_size (could add 10-20 points)")
        if not lead.get_field('patient_volume'):
            missing_fields.append("patient_volume (could add 10-20 points)")
        if not lead.has_field('calendly_url'):
            missing_fields.append("calendly_url (could add 10 points)")
        if not lead.is_complete():
            missing_fields.append("complete_response (could add 10 points)")

        breakdown = QualificationBreakdown(
            total_score=result.score,
            tier=result.tier.value,
            is_qualified=result.is_qualified,
            criteria={
                "business_size": result.criteria.business_size_score,
                "patient_volume": result.criteria.patient_volume_score,
                "industry_fit": result.criteria.industry_fit_score,
                "response_completeness": result.criteria.response_completeness_score,
                "calendly_booking": result.criteria.calendly_booking_score,
                "response_quality": result.criteria.response_quality_score,
                "company_data": result.criteria.company_data_score,
            },
            reasoning=result.reasoning,
            key_factors=result.key_factors,
            concerns=result.concerns,
            missing_fields=missing_fields,
            processing_time_ms=result.processing_time_ms
        )

        return {
            "lead_id": lead.id,
            "breakdown": breakdown.model_dump(),
            "raw_answers": lead.raw_answers,  # Show what data is actually available
            "next_actions": result.next_actions
        }

    def _test_qualification(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test qualification with sample data (validation mode)."""
        return self._explain_qualification(None, test_data)


# ===== Singleton Instance =====

_introspection_service: Optional[AgentIntrospectionService] = None

def get_introspection_service() -> AgentIntrospectionService:
    """Get singleton introspection service instance."""
    global _introspection_service
    if _introspection_service is None:
        _introspection_service = AgentIntrospectionService()
    return _introspection_service
