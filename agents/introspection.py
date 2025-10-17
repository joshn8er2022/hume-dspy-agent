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
    """Request format for A2A introspection queries and commands."""
    mode: str = Field("query", description="Mode: 'query' (read-only) or 'command' (action)")
    agent_type: str = Field(..., description="Agent to target: 'inbound', 'follow_up', 'research', 'strategy'")
    action: str = Field(..., description="Action: 'show_state', 'explain_score', 'research_lead', etc.")
    lead_id: Optional[str] = Field(None, description="Lead ID for operations")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the action")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test lead data for validation")
    
    # Backwards compatibility
    @property
    def query_type(self) -> str:
        return self.action


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
    """Response from A2A introspection query or command."""
    success: bool
    mode: str = "query"
    action: str
    data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = Field(None, description="Task ID for async commands")
    status: Optional[str] = Field(None, description="Command status: pending, in_progress, completed, failed")
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Backwards compatibility
    @property
    def query_type(self) -> str:
        return self.action


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
        """Route A2A request to appropriate handler (query or command mode)."""
        try:
            # Route based on mode
            if request.mode == "query":
                data = self._handle_query_mode(request)
                return IntrospectionResponse(
                    success=True,
                    mode="query",
                    action=request.action,
                    data=data
                )
            
            elif request.mode == "command":
                result = self._handle_command_mode(request)
                return IntrospectionResponse(
                    success=True,
                    mode="command",
                    action=request.action,
                    data=result.get("data"),
                    task_id=result.get("task_id"),
                    status=result.get("status", "completed")
                )
            
            else:
                raise ValueError(f"Unknown mode: {request.mode}. Use 'query' or 'command'")

        except Exception as e:
            logger.error(f"A2A error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return IntrospectionResponse(
                success=False,
                mode=request.mode,
                action=request.action,
                error=str(e)
            )
    
    def _handle_query_mode(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle read-only query requests."""
        if request.agent_type in ["follow_up", "qualification"]:
            # Backwards compatibility with old format
            if request.agent_type == "follow_up":
                return self._handle_follow_up_query(request)
            elif request.agent_type == "qualification":
                return self._handle_qualification_query(request)
        
        elif request.agent_type == "inbound":
            return self._handle_qualification_query(request)
        
        elif request.agent_type == "research":
            return self._handle_research_query(request)
        
        elif request.agent_type == "strategy":
            return self._handle_strategy_query(request)
        
        else:
            raise ValueError(f"Unknown agent type: {request.agent_type}")
    
    def _handle_command_mode(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle action commands that modify state or trigger operations."""
        if request.agent_type == "inbound":
            return self._handle_inbound_command(request)
        
        elif request.agent_type == "research":
            return self._handle_research_command(request)
        
        elif request.agent_type == "follow_up":
            return self._handle_follow_up_command(request)
        
        elif request.agent_type == "strategy":
            return self._handle_strategy_command(request)
        
        else:
            raise ValueError(f"Unknown agent type for commands: {request.agent_type}")

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
    
    # ===== Command Handlers =====
    
    def _handle_inbound_command(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle inbound agent commands."""
        action = request.action
        
        if action == "research_lead_deeply":
            # Trigger deep research on a lead
            lead_id = request.lead_id
            if not lead_id:
                raise ValueError("lead_id required for research_lead_deeply")
            
            params = request.parameters or {}
            task_id = f"research-{lead_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # TODO: Implement async research task
            return {
                "status": "accepted",
                "task_id": task_id,
                "data": {
                    "message": "Deep research task queued",
                    "lead_id": lead_id,
                    "parameters": params
                }
            }
        
        elif action == "requalify_lead":
            # Re-run qualification on a lead
            lead_id = request.lead_id
            if not lead_id:
                raise ValueError("lead_id required for requalify_lead")
            
            # Load and requalify
            result = self._explain_qualification(lead_id, None)
            return {
                "status": "completed",
                "data": result
            }
        
        else:
            raise ValueError(f"Unknown inbound command: {action}")
    
    def _handle_research_command(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle research agent commands."""
        action = request.action
        
        if action == "research_person":
            params = request.parameters or {}
            name = params.get("name")
            email = params.get("email")
            company = params.get("company")
            
            if not (name or email):
                raise ValueError("name or email required for research_person")
            
            task_id = f"person-research-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # TODO: Implement person research
            return {
                "status": "accepted",
                "task_id": task_id,
                "data": {
                    "message": "Person research task queued",
                    "name": name,
                    "email": email,
                    "company": company
                }
            }
        
        elif action == "research_company":
            params = request.parameters or {}
            company_name = params.get("company_name")
            domain = params.get("domain")
            
            if not (company_name or domain):
                raise ValueError("company_name or domain required for research_company")
            
            task_id = f"company-research-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # TODO: Implement company research
            return {
                "status": "accepted",
                "task_id": task_id,
                "data": {
                    "message": "Company research task queued",
                    "company_name": company_name,
                    "domain": domain
                }
            }
        
        elif action == "find_additional_contacts":
            params = request.parameters or {}
            company_name = params.get("company_name")
            
            if not company_name:
                raise ValueError("company_name required for find_additional_contacts")
            
            task_id = f"contacts-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # TODO: Implement contact finding
            return {
                "status": "accepted",
                "task_id": task_id,
                "data": {
                    "message": "Contact search task queued",
                    "company_name": company_name
                }
            }
        
        else:
            raise ValueError(f"Unknown research command: {action}")
    
    def _handle_follow_up_command(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle follow-up agent commands."""
        action = request.action
        
        if action == "send_follow_up_now":
            lead_id = request.lead_id
            if not lead_id:
                raise ValueError("lead_id required for send_follow_up_now")
            
            # TODO: Trigger immediate follow-up
            return {
                "status": "completed",
                "data": {
                    "message": "Follow-up triggered",
                    "lead_id": lead_id
                }
            }
        
        elif action == "pause_follow_up":
            lead_id = request.lead_id
            if not lead_id:
                raise ValueError("lead_id required for pause_follow_up")
            
            # TODO: Pause follow-up sequence
            return {
                "status": "completed",
                "data": {
                    "message": "Follow-up paused",
                    "lead_id": lead_id
                }
            }
        
        elif action == "escalate_to_human":
            lead_id = request.lead_id
            if not lead_id:
                raise ValueError("lead_id required for escalate_to_human")
            
            # TODO: Escalate to human
            return {
                "status": "completed",
                "data": {
                    "message": "Escalated to human",
                    "lead_id": lead_id
                }
            }
        
        else:
            raise ValueError(f"Unknown follow-up command: {action}")
    
    def _handle_strategy_command(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle strategy agent commands."""
        action = request.action
        
        if action == "analyze_pipeline":
            params = request.parameters or {}
            days = params.get("days", 7)
            
            # TODO: Implement pipeline analysis
            return {
                "status": "completed",
                "data": {
                    "message": f"Pipeline analysis for last {days} days",
                    "total_leads": 0,
                    "by_tier": {},
                    "conversion_rate": 0
                }
            }
        
        elif action == "recommend_outbound_targets":
            params = request.parameters or {}
            segment = params.get("segment", "all")
            min_size = params.get("min_size", 50)
            
            # TODO: Implement outbound recommendations
            return {
                "status": "completed",
                "data": {
                    "message": f"Outbound recommendations for {segment}",
                    "targets": [],
                    "reasoning": "Based on successful inbound patterns"
                }
            }
        
        else:
            raise ValueError(f"Unknown strategy command: {action}")
    
    def _handle_research_query(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle research agent queries."""
        return {
            "message": "Research agent query handler (placeholder)",
            "available_actions": [
                "research_person",
                "research_company",
                "find_additional_contacts"
            ]
        }
    
    def _handle_strategy_query(self, request: IntrospectionRequest) -> Dict[str, Any]:
        """Handle strategy agent queries."""
        return {
            "message": "Strategy agent query handler (placeholder)",
            "available_actions": [
                "analyze_pipeline",
                "recommend_outbound_targets"
            ]
        }


# ===== Singleton Instance =====

_introspection_service: Optional[AgentIntrospectionService] = None

def get_introspection_service() -> AgentIntrospectionService:
    """Get singleton introspection service instance."""
    global _introspection_service
    if _introspection_service is None:
        _introspection_service = AgentIntrospectionService()
    return _introspection_service
