"""
ABM Campaign Workflow - LangGraph Implementation

Stateful workflow for multi-contact ABM campaigns with:
- State management across campaign lifecycle
- Conditional routing based on responses
- Autonomous decision-making nodes
- Error handling and recovery
"""

import logging
from typing import Dict, List, Optional, TypedDict, Annotated
from datetime import datetime
import operator

try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolExecutor
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logging.warning("LangGraph not available, using fallback implementation")

from agents.account_orchestrator import AccountOrchestrator, CampaignStatus, CampaignChannel

logger = logging.getLogger(__name__)


class CampaignState(TypedDict):
    """State schema for ABM campaign workflow"""
    campaign_id: str
    account_id: str
    status: str
    current_step: int
    contacts: List[Dict]
    touchpoints: Annotated[List[Dict], operator.add]
    responses: Annotated[List[Dict], operator.add]
    conflicts: List[Dict]
    next_action: Optional[str]
    error: Optional[str]
    metadata: Dict


class ABMCampaignWorkflow:
    """
    LangGraph-based workflow for ABM campaign execution.
    
    Workflow Nodes:
    - initialize: Set up campaign structure
    - check_conflicts: Detect response conflicts
    - select_contact: Choose next contact to engage
    - select_channel: Determine communication channel
    - generate_message: Create personalized content
    - execute_touchpoint: Send message
    - evaluate_response: Check for engagement
    - schedule_next: Plan next touchpoint
    - complete: Finalize campaign
    """
    
    def __init__(self, orchestrator: AccountOrchestrator):
        """
        Initialize workflow with orchestrator.
        
        Args:
            orchestrator: AccountOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.graph = None
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
        
        logger.info("ABMCampaignWorkflow initialized")
    
    def _build_graph(self):
        """Build LangGraph workflow"""
        workflow = StateGraph(CampaignState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("check_conflicts", self._check_conflicts_node)
        workflow.add_node("select_contact", self._select_contact_node)
        workflow.add_node("select_channel", self._select_channel_node)
        workflow.add_node("generate_message", self._generate_message_node)
        workflow.add_node("execute_touchpoint", self._execute_touchpoint_node)
        workflow.add_node("evaluate_response", self._evaluate_response_node)
        workflow.add_node("schedule_next", self._schedule_next_node)
        workflow.add_node("complete", self._complete_node)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # Add edges
        workflow.add_edge("initialize", "check_conflicts")
        
        # Conditional routing from conflict check
        workflow.add_conditional_edges(
            "check_conflicts",
            self._route_after_conflict_check,
            {
                "continue": "select_contact",
                "pause": "complete",
                "error": "complete"
            }
        )
        
        workflow.add_edge("select_contact", "select_channel")
        workflow.add_edge("select_channel", "generate_message")
        workflow.add_edge("generate_message", "execute_touchpoint")
        workflow.add_edge("execute_touchpoint", "evaluate_response")
        
        # Conditional routing from response evaluation
        workflow.add_conditional_edges(
            "evaluate_response",
            self._route_after_evaluation,
            {
                "schedule_next": "schedule_next",
                "complete": "complete"
            }
        )
        
        workflow.add_edge("schedule_next", END)
        workflow.add_edge("complete", END)
        
        self.graph = workflow.compile()
        logger.info("LangGraph workflow compiled")
    
    async def _initialize_node(self, state: CampaignState) -> CampaignState:
        """Initialize campaign state"""
        logger.info(f"Initializing campaign: {state.get('campaign_id')}")
        
        # Set defaults if not present
        if "touchpoints" not in state:
            state["touchpoints"] = []
        if "responses" not in state:
            state["responses"] = []
        if "conflicts" not in state:
            state["conflicts"] = []
        if "current_step" not in state:
            state["current_step"] = 0
        if "metadata" not in state:
            state["metadata"] = {}
        
        state["metadata"]["initialized_at"] = datetime.utcnow().isoformat()
        
        return state
    
    async def _check_conflicts_node(self, state: CampaignState) -> CampaignState:
        """Check for campaign conflicts"""
        logger.info(f"Checking conflicts for campaign: {state['campaign_id']}")
        
        try:
            conflict_result = await self.orchestrator.check_conflicts(state["campaign_id"])
            
            state["conflicts"] = conflict_result.get("conflicts", [])
            
            if conflict_result.get("has_conflict"):
                state["next_action"] = "pause"
                state["metadata"]["pause_reason"] = conflict_result["conflicts"][0]["type"]
            else:
                state["next_action"] = "continue"
            
        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}")
            state["error"] = str(e)
            state["next_action"] = "error"
        
        return state
    
    def _route_after_conflict_check(self, state: CampaignState) -> str:
        """Route based on conflict check result"""
        return state.get("next_action", "continue")
    
    async def _select_contact_node(self, state: CampaignState) -> CampaignState:
        """Select next contact to engage"""
        logger.info(f"Selecting contact for step {state['current_step']}")
        
        try:
            # Build campaign dict for orchestrator
            campaign = {
                "campaign_id": state["campaign_id"],
                "contacts": state["contacts"],
                "touchpoints": state["touchpoints"],
                "current_step": state["current_step"]
            }
            
            selected_contact = self.orchestrator._select_next_contact(campaign)
            state["metadata"]["selected_contact"] = selected_contact
            
        except Exception as e:
            logger.error(f"Error selecting contact: {str(e)}")
            state["error"] = str(e)
        
        return state
    
    async def _select_channel_node(self, state: CampaignState) -> CampaignState:
        """Select communication channel"""
        logger.info("Selecting communication channel")
        
        try:
            campaign = {
                "campaign_id": state["campaign_id"],
                "contacts": state["contacts"],
                "touchpoints": state["touchpoints"],
                "current_step": state["current_step"]
            }
            
            contact = state["metadata"]["selected_contact"]
            channel = self.orchestrator.select_channel(campaign, contact)
            
            state["metadata"]["selected_channel"] = channel
            
        except Exception as e:
            logger.error(f"Error selecting channel: {str(e)}")
            state["error"] = str(e)
        
        return state
    
    async def _generate_message_node(self, state: CampaignState) -> CampaignState:
        """Generate personalized message"""
        logger.info("Generating message content")
        
        try:
            campaign = {
                "campaign_id": state["campaign_id"],
                "contacts": state["contacts"],
                "touchpoints": state["touchpoints"],
                "current_step": state["current_step"],
                "metadata": state["metadata"]
            }
            
            contact = state["metadata"]["selected_contact"]
            channel = state["metadata"]["selected_channel"]
            
            message = await self.orchestrator.generate_message(campaign, contact, channel)
            state["metadata"]["generated_message"] = message
            
        except Exception as e:
            logger.error(f"Error generating message: {str(e)}")
            state["error"] = str(e)
        
        return state
    
    async def _execute_touchpoint_node(self, state: CampaignState) -> CampaignState:
        """Execute touchpoint (send message)"""
        logger.info("Executing touchpoint")
        
        try:
            contact = state["metadata"]["selected_contact"]
            channel = state["metadata"]["selected_channel"]
            message = state["metadata"]["generated_message"]
            
            touchpoint = await self.orchestrator._execute_touchpoint(
                state["campaign_id"],
                contact,
                channel,
                message
            )
            
            # Add to state (will be appended due to Annotated[List, operator.add])
            state["touchpoints"] = [touchpoint]
            state["current_step"] += 1
            
        except Exception as e:
            logger.error(f"Error executing touchpoint: {str(e)}")
            state["error"] = str(e)
        
        return state
    
    async def _evaluate_response_node(self, state: CampaignState) -> CampaignState:
        """Evaluate if response received or next step needed"""
        logger.info("Evaluating campaign progress")
        
        try:
            # Check if max touchpoints reached
            max_touchpoints = self.orchestrator.config["max_touchpoints"]
            
            if state["current_step"] >= max_touchpoints:
                state["next_action"] = "complete"
                state["status"] = CampaignStatus.COMPLETED.value
            elif state.get("error"):
                state["next_action"] = "complete"
                state["status"] = CampaignStatus.CANCELLED.value
            else:
                state["next_action"] = "schedule_next"
                state["status"] = CampaignStatus.ACTIVE.value
            
        except Exception as e:
            logger.error(f"Error evaluating response: {str(e)}")
            state["error"] = str(e)
            state["next_action"] = "complete"
        
        return state
    
    def _route_after_evaluation(self, state: CampaignState) -> str:
        """Route based on evaluation result"""
        return state.get("next_action", "complete")
    
    async def _schedule_next_node(self, state: CampaignState) -> CampaignState:
        """Schedule next touchpoint"""
        logger.info("Scheduling next touchpoint")
        
        try:
            next_touchpoint = await self.orchestrator.schedule_next_touchpoint(
                state["campaign_id"]
            )
            
            state["metadata"]["next_touchpoint"] = next_touchpoint
            
        except Exception as e:
            logger.error(f"Error scheduling next touchpoint: {str(e)}")
            state["error"] = str(e)
        
        return state
    
    async def _complete_node(self, state: CampaignState) -> CampaignState:
        """Complete campaign"""
        logger.info(f"Completing campaign: {state['campaign_id']}")
        
        state["metadata"]["completed_at"] = datetime.utcnow().isoformat()
        
        if not state.get("status"):
            state["status"] = CampaignStatus.COMPLETED.value
        
        return state
    
    async def execute(self, initial_state: CampaignState) -> CampaignState:
        """
        Execute workflow with initial state.
        
        Args:
            initial_state: Initial campaign state
            
        Returns:
            Final campaign state
        """
        if LANGGRAPH_AVAILABLE and self.graph:
            # Use LangGraph execution
            result = await self.graph.ainvoke(initial_state)
            return result
        else:
            # Fallback to sequential execution
            return await self._execute_fallback(initial_state)
    
    async def _execute_fallback(self, state: CampaignState) -> CampaignState:
        """Fallback execution without LangGraph"""
        logger.info("Executing workflow in fallback mode")
        
        # Initialize
        state = await self._initialize_node(state)
        
        # Check conflicts
        state = await self._check_conflicts_node(state)
        if state.get("next_action") != "continue":
            return await self._complete_node(state)
        
        # Select contact
        state = await self._select_contact_node(state)
        if state.get("error"):
            return await self._complete_node(state)
        
        # Select channel
        state = await self._select_channel_node(state)
        if state.get("error"):
            return await self._complete_node(state)
        
        # Generate message
        state = await self._generate_message_node(state)
        if state.get("error"):
            return await self._complete_node(state)
        
        # Execute touchpoint
        state = await self._execute_touchpoint_node(state)
        if state.get("error"):
            return await self._complete_node(state)
        
        # Evaluate
        state = await self._evaluate_response_node(state)
        
        # Schedule next or complete
        if state.get("next_action") == "schedule_next":
            state = await self._schedule_next_node(state)
        
        return await self._complete_node(state)
    
    def visualize(self, output_path: str = "abm_workflow.png"):
        """Generate workflow visualization"""
        if not LANGGRAPH_AVAILABLE or not self.graph:
            logger.warning("LangGraph not available, cannot visualize")
            return
        
        try:
            from IPython.display import Image, display
            display(Image(self.graph.get_graph().draw_mermaid_png()))
        except Exception as e:
            logger.error(f"Error visualizing workflow: {str(e)}")


class ABMCampaignBuilder:
    """Builder for creating ABM campaign workflows"""
    
    def __init__(self):
        self.orchestrator = None
        self.config = {}
    
    def with_orchestrator(self, orchestrator: AccountOrchestrator):
        """Set orchestrator instance"""
        self.orchestrator = orchestrator
        return self
    
    def with_config(self, config: Dict):
        """Set workflow configuration"""
        self.config = config
        return self
    
    def build(self) -> ABMCampaignWorkflow:
        """Build workflow instance"""
        if not self.orchestrator:
            raise ValueError("Orchestrator required")
        
        # Apply config to orchestrator
        if self.config:
            self.orchestrator.config.update(self.config)
        
        return ABMCampaignWorkflow(self.orchestrator)


def create_campaign_workflow(orchestrator: AccountOrchestrator,
                            config: Optional[Dict] = None) -> ABMCampaignWorkflow:
    """
    Factory function to create ABM campaign workflow.
    
    Args:
        orchestrator: AccountOrchestrator instance
        config: Optional workflow configuration
        
    Returns:
        Configured ABMCampaignWorkflow
    """
    builder = ABMCampaignBuilder()
    builder.with_orchestrator(orchestrator)
    
    if config:
        builder.with_config(config)
    
    return builder.build()
