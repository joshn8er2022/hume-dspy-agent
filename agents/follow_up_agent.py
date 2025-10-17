"""LangGraph-based Autonomous Follow-up Agent.

This agent manages the entire lead journey autonomously:
- Sends initial engagement emails
- Monitors for responses
- Schedules and sends follow-ups
- Updates Slack thread with progress
- Escalates hot leads
"""

from typing import Literal, TypedDict
from datetime import datetime
import os
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from models import Lead, LeadTier, LeadStatus
from utils.slack_client import SlackClient
from utils.email_client import EmailClient

logger = logging.getLogger(__name__)


# Define the agent state
class LeadJourneyState(TypedDict):
    """State for tracking a lead's autonomous journey."""
    lead_id: str
    email: str
    first_name: str
    company: str
    tier: str
    status: str
    slack_thread_ts: str | None
    slack_channel: str | None
    email_sent: bool
    email_sent_at: datetime | None
    follow_up_count: int
    last_follow_up_at: datetime | None
    response_received: bool
    next_follow_up_hours: int
    escalated: bool
    error: str | None


class FollowUpAgent:
    """Autonomous agent for managing lead follow-ups using LangGraph."""

    def __init__(self):
        self.slack = SlackClient()
        self.email_client = EmailClient()

        # Initialize LLM with OpenRouter Sonnet 4.5 (fallback to Anthropic direct)
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if openrouter_api_key:
            # Use OpenRouter with Sonnet 4.5
            self.llm = ChatOpenAI(
                model="anthropic/claude-sonnet-4-5",
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.7,
            )
            logger.info("✅ Follow-up agent using OpenRouter Sonnet 4.5")
        elif anthropic_api_key:
            # Fallback to Anthropic direct
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(
                model="claude-3-5-sonnet-20241022",
                api_key=anthropic_api_key,
                temperature=0.7,
            )
            logger.info("✅ Follow-up agent using Anthropic direct (fallback)")
        else:
            self.llm = None
            logger.warning("⚠️ No LLM configured for follow-up agent")

        # Build the state graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine for lead journey."""

        workflow = StateGraph(LeadJourneyState)

        # Define nodes (agent actions)
        workflow.add_node("assess_lead", self.assess_lead)
        workflow.add_node("send_initial_email", self.send_initial_email)
        workflow.add_node("wait_for_response", self.wait_for_response)
        workflow.add_node("send_follow_up", self.send_follow_up)
        workflow.add_node("update_slack", self.update_slack)
        workflow.add_node("escalate_hot_lead", self.escalate_hot_lead)
        workflow.add_node("mark_cold", self.mark_cold)

        # Define edges (state transitions)
        workflow.set_entry_point("assess_lead")

        workflow.add_conditional_edges(
            "assess_lead",
            self.should_send_initial_email,
            {
                "send_email": "send_initial_email",
                "skip": "update_slack",
            }
        )

        workflow.add_edge("send_initial_email", "update_slack")
        workflow.add_edge("update_slack", "wait_for_response")

        workflow.add_conditional_edges(
            "wait_for_response",
            self.check_response_status,
            {
                "responded": "escalate_hot_lead",
                "no_response_continue": "send_follow_up",
                "no_response_stop": "mark_cold",
            }
        )

        workflow.add_edge("send_follow_up", "update_slack")
        workflow.add_edge("escalate_hot_lead", END)
        workflow.add_edge("mark_cold", END)

        # Compile with memory for persistence
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    # ===== NODES (Actions) =====

    def assess_lead(self, state: LeadJourneyState) -> LeadJourneyState:
        """Assess the lead and determine initial strategy."""

        # Set defaults based on tier
        if state['tier'] == LeadTier.HOT.value:
            state['next_follow_up_hours'] = 4  # Follow up every 4 hours
        elif state['tier'] == LeadTier.WARM.value:
            state['next_follow_up_hours'] = 24  # Follow up daily
        else:
            state['next_follow_up_hours'] = 48  # Follow up every 2 days

        logger.info(f"Assessed lead {state['lead_id']}: tier={state['tier']}, cadence={state['next_follow_up_hours']}h")
        return state

    def send_initial_email(self, state: LeadJourneyState) -> LeadJourneyState:
        """Send the initial engagement email."""
        try:
            # Prepare lead data for personalization
            lead_data = {
                'first_name': state.get('first_name', ''),
                'company': state.get('company', 'your practice')
            }

            success = self.email_client.send_email(
                to_email=state['email'],
                lead_id=state['lead_id'],
                template_type='initial_outreach',
                tier=state['tier'],
                lead_data=lead_data
            )

            if success:
                state['email_sent'] = True
                state['email_sent_at'] = datetime.utcnow()
                state['status'] = LeadStatus.CONTACTED.value
                logger.info(f"Initial email sent to {state['email']}")
            else:
                state['error'] = "Failed to send initial email"

        except Exception as e:
            state['error'] = f"Email error: {str(e)}"
            logger.error(state['error'])

        return state

    def send_follow_up(self, state: LeadJourneyState) -> LeadJourneyState:
        """Send a follow-up email."""
        try:
            state['follow_up_count'] += 1

            # Prepare lead data for personalization
            lead_data = {
                'first_name': state.get('first_name', ''),
                'company': state.get('company', 'your practice')
            }

            success = self.email_client.send_email(
                to_email=state['email'],
                lead_id=state['lead_id'],
                template_type=f'follow_up_{state["follow_up_count"]}',
                tier=state['tier'],
                lead_data=lead_data
            )

            if success:
                state['last_follow_up_at'] = datetime.utcnow()
                state['status'] = LeadStatus.FOLLOWING_UP.value
                logger.info(f"Follow-up #{state['follow_up_count']} sent to {state['email']}")
            else:
                state['error'] = "Failed to send follow-up email"

        except Exception as e:
            state['error'] = f"Follow-up error: {str(e)}"
            logger.error(state['error'])

        return state

    def wait_for_response(self, state: LeadJourneyState) -> LeadJourneyState:
        """This is a placeholder - actual waiting happens via Celery scheduling."""
        state['status'] = LeadStatus.AWAITING_RESPONSE.value
        return state

    def update_slack(self, state: LeadJourneyState) -> LeadJourneyState:
        """Update the Slack thread with progress."""
        try:
            if not state.get('slack_thread_ts'):
                return state

            # Determine message based on state
            if state['email_sent'] and state['follow_up_count'] == 0:
                message = f"✅ Initial outreach email sent to {state['first_name']}\n⏳ Waiting for response..."

            elif state['follow_up_count'] > 0:
                hours_since_last = (
                    datetime.utcnow() - state['last_follow_up_at']
                ).total_seconds() / 3600 if state['last_follow_up_at'] else 0

                message = f"📧 Follow-up #{state['follow_up_count']} sent to {state['first_name']}\n"
                message += f"⏱️ Last contact: {int(hours_since_last)}h ago\n"
                message += f"⏳ Next follow-up in {state['next_follow_up_hours']}h"

            else:
                message = f"👀 Lead {state['first_name']} is being monitored"

            # Post as thread reply
            self.slack.post_thread_reply(
                channel=state['slack_channel'],
                thread_ts=state['slack_thread_ts'],
                text=message
            )
            logger.info(f"Slack updated for lead {state['lead_id']}")

        except Exception as e:
            state['error'] = f"Slack update error: {str(e)}"
            logger.error(state['error'])

        return state

    def escalate_hot_lead(self, state: LeadJourneyState) -> LeadJourneyState:
        """Escalate a hot lead that responded."""
        try:
            message = f"""
🔥🔥🔥 HOT LEAD RESPONSE RECEIVED! 🔥🔥🔥

{state['first_name']} ({state['email']}) has responded!

Tier: {state['tier']}
Follow-ups sent: {state['follow_up_count']}

@channel - Someone should reach out ASAP!
"""

            self.slack.post_thread_reply(
                channel=state['slack_channel'],
                thread_ts=state['slack_thread_ts'],
                text=message
            )

            state['status'] = LeadStatus.RESPONDED.value
            state['escalated'] = True
            logger.info(f"Hot lead escalated: {state['lead_id']}")

        except Exception as e:
            state['error'] = f"Escalation error: {str(e)}"
            logger.error(state['error'])

        return state

    def mark_cold(self, state: LeadJourneyState) -> LeadJourneyState:
        """Mark lead as cold after max follow-ups."""
        try:
            message = f"""
❄️ Lead marked as COLD: {state['first_name']}

Total follow-ups sent: {state['follow_up_count']}
No response received after {state['follow_up_count']} attempts.

Moving to nurture campaign.
"""

            self.slack.post_thread_reply(
                channel=state['slack_channel'],
                thread_ts=state['slack_thread_ts'],
                text=message
            )

            state['status'] = LeadStatus.COLD.value
            logger.info(f"Lead marked cold: {state['lead_id']}")

        except Exception as e:
            state['error'] = f"Mark cold error: {str(e)}"
            logger.error(state['error'])

        return state

    # ===== CONDITIONAL EDGES (Decision Points) =====

    def should_send_initial_email(self, state: LeadJourneyState) -> Literal["send_email", "skip"]:
        """Decide if we should send initial email."""
        if state['email_sent'] or state['tier'] == LeadTier.UNQUALIFIED.value:
            return "skip"
        return "send_email"

    def check_response_status(
        self, state: LeadJourneyState
    ) -> Literal["responded", "no_response_continue", "no_response_stop"]:
        """Check if lead responded and decide next action."""

        if state['response_received']:
            return "responded"

        # Check if we've hit max follow-ups
        max_follow_ups = {
            LeadTier.HOT.value: 5,
            LeadTier.WARM.value: 3,
            LeadTier.COLD.value: 2,
        }.get(state['tier'], 2)

        if state['follow_up_count'] >= max_follow_ups:
            return "no_response_stop"

        return "no_response_continue"

    # ===== PUBLIC API =====

    def start_lead_journey(
        self,
        lead: Lead,
        tier: LeadTier,
        slack_thread_ts: str,
        slack_channel: str = "inbound-leads"
    ) -> dict:
        """Start the autonomous journey for a new lead."""

        initial_state: LeadJourneyState = {
            "lead_id": lead.id,
            "email": lead.email,
            "first_name": lead.first_name or "there",
            "tier": tier.value,
            "status": LeadStatus.NEW.value,
            "slack_thread_ts": slack_thread_ts,
            "slack_channel": slack_channel,
            "email_sent": False,
            "email_sent_at": None,
            "follow_up_count": 0,
            "last_follow_up_at": None,
            "response_received": False,
            "next_follow_up_hours": 24,
            "escalated": False,
            "error": None,
        }

        config = {"configurable": {"thread_id": lead.id}}
        result = self.graph.invoke(initial_state, config)

        return result

    def continue_lead_journey(
        self,
        lead_id: str,
        response_received: bool = False
    ) -> dict:
        """Continue the journey for an existing lead (called by scheduled task)."""

        config = {"configurable": {"thread_id": lead_id}}
        current_state = self.graph.get_state(config)

        if response_received:
            current_state.values['response_received'] = True

        result = self.graph.invoke(None, config)
        return result
