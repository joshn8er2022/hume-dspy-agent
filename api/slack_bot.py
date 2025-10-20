"""Slack Bot for Personal Agent Communication.

This bot allows Josh to interact with all agents via Slack DM:
- Call specific agents ("call research agent")
- Query agent state ("show inbound status")
- Issue commands ("research lead abc-123")
- Get strategic insights ("what should I focus on?")
"""

import logging
import os
import dspy
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from collections import OrderedDict

from fastapi import APIRouter, Request, HTTPException
import httpx

from agents.strategy_agent import StrategyAgent
from agents.introspection import get_introspection_service
from dspy_modules.conversation_signatures import (
    GenerateHelpMessage,
    GenerateAgentMenu,
    ListAgents,
    QuickPipelineStatus,
    HandleUnknownCommand,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/slack", tags=["slack"])

# Initialize Strategy Agent (handles all agent coordination)
strategy_agent = StrategyAgent()

# Event deduplication cache (prevents duplicate responses from Slack retries)
# Phase 0 Fix #3: Enhanced with time-based expiration
processed_events: OrderedDict[str, float] = OrderedDict()
MAX_CACHE_SIZE = 100
EVENT_EXPIRY_SECONDS = 300  # Remove events older than 5 minutes

# Initialize DSPy modules for Slack interface
try:
    help_generator = dspy.ChainOfThought(GenerateHelpMessage)
    agent_menu_generator = dspy.ChainOfThought(GenerateAgentMenu)
    agents_lister = dspy.ChainOfThought(ListAgents)
    pipeline_status = dspy.ChainOfThought(QuickPipelineStatus)
    unknown_handler = dspy.ChainOfThought(HandleUnknownCommand)
    logger.info("✅ Slack bot DSPy modules initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Slack DSPy modules: {e}")
    help_generator = None
    agent_menu_generator = None
    agents_lister = None
    pipeline_status = None
    unknown_handler = None


# ============================================================================
# SLACK EVENT HANDLING
# ============================================================================

@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack events (messages, mentions, etc.).
    
    This is the main entry point for Slack interactions.
    """
    try:
        payload = await request.json()
        
        # Handle URL verification challenge (Slack setup)
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}
        
        # Handle actual events
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            
            # Ignore bot messages (prevent loops)
            if event.get("bot_id"):
                return {"ok": True}
            
            # Handle app mentions and DMs
            if event.get("type") in ["app_mention", "message"]:
                # Create unique event ID
                event_id = f"{event.get('ts')}_{event.get('user')}_{event.get('channel')}"
                
                # Phase 0 Fix #3: Clean up old events first (time-based expiration)
                current_time = time.time()
                expired_events = [
                    eid for eid, timestamp in processed_events.items()
                    if current_time - timestamp > EVENT_EXPIRY_SECONDS
                ]
                for eid in expired_events:
                    del processed_events[eid]
                
                # Check for duplicate (Slack retries if we don't respond in 3 seconds)
                if event_id in processed_events:
                    logger.warning(f"⚠️ Duplicate Slack event (retry detected): {event_id}")
                    return {"ok": True}  # Return 200 but don't process
                
                # Mark as processing immediately
                processed_events[event_id] = current_time
                
                # Limit cache size (backup to time-based cleanup)
                if len(processed_events) > MAX_CACHE_SIZE:
                    processed_events.popitem(last=False)  # Remove oldest
                
                # Process in background (don't block Slack webhook response)
                asyncio.create_task(handle_message_async(event, event_id))
            
            return {"ok": True}  # Return immediately to prevent Slack retries
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"❌ Slack event error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def handle_message_async(event: Dict[str, Any], event_id: str):
    """Process incoming Slack message asynchronously (doesn't block webhook).
    
    Args:
        event: Slack event data containing message info
        event_id: Unique event identifier for deduplication
    """
    try:
        text = event.get("text", "").strip()
        user = event.get("user")
        channel = event.get("channel")
        ts = event.get("ts")
        
        # Remove bot mention if present
        text = text.replace("<@U0935UUHRC7>", "").strip()  # Bot user ID
        
        logger.info(f"💬 Slack message from {user} [Event: {event_id}]")
        logger.info(f"   Message: {text[:100]}...")
        
        # Parse command and route to appropriate handler
        response = await route_command(text, user)
        
        # Send response to Slack
        await strategy_agent.send_slack_message(
            message=response,
            channel=channel,
            thread_ts=ts
        )
        
        logger.info(f"✅ Response sent [Event: {event_id}]")
    
    except Exception as e:
        logger.error(f"❌ Message handling error [Event: {event_id}]: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await strategy_agent.send_slack_message(
                message=f"❌ Error: {str(e)}",
                channel=event.get("channel")
            )
        except:
            pass  # Don't fail if error response also fails


# ============================================================================
# COMMAND ROUTING
# ============================================================================

async def route_command(text: str, user: str) -> str:
    """Route Slack command to appropriate agent.
    
    Supports commands like:
    - "call research agent"
    - "show inbound status"
    - "research lead abc-123"
    - "what should I focus on?"
    
    Args:
        text: Message text from user
        user: User ID who sent message
    
    Returns:
        Response text to send back to Slack
    """
    text_lower = text.lower()
    
    # ===== AGENT CALLER COMMANDS =====
    
    # Call Research Agent
    if any(word in text_lower for word in ["call research", "research agent", "talk to research"]):
        return await call_research_agent(text)
    
    # Call Inbound Agent
    elif any(word in text_lower for word in ["call inbound", "inbound agent", "qualification"]):
        return await call_inbound_agent(text)
    
    # Call Follow-Up Agent
    elif any(word in text_lower for word in ["call follow", "follow-up agent", "followup"]):
        return await call_followup_agent(text)
    
    # ===== QUICK COMMANDS =====
    
    # Show pipeline status
    elif any(word in text_lower for word in ["pipeline", "status", "how many leads"]):
        return await quick_pipeline_status()
    
    # Research a lead
    elif "research lead" in text_lower or "research" in text_lower:
        return await quick_research_lead(text)
    
    # List agents
    elif any(word in text_lower for word in ["list agents", "show agents", "available agents"]):
        return get_available_agents(user_question=text)
    
    # Help
    elif any(word in text_lower for word in ["help", "what can you do", "commands"]):
        return get_help_message(user_message=text)
    
    # ===== DEFAULT: Strategy Agent Conversational (Pure DSPy) =====
    else:
        # Pass user ID for conversation history tracking
        return await strategy_agent.chat_with_josh(text, user_id=user)


# ============================================================================
# AGENT CALLERS
# ============================================================================

async def call_research_agent(text: str) -> str:
    """Call the Research Agent - DSPy generates contextual menu.
    
    Args:
        text: Original message text (user context)
    
    Returns:
        DSPy-generated menu with capabilities and examples
    """
    if not agent_menu_generator:
        return "❌ Agent menu generator not configured"
    
    try:
        # Build agent capabilities dynamically
        capabilities = """Person research (Clearbit), Company research (Apollo), 
Contact discovery, Competitive intelligence, Lead deep-dive"""
        
        # Check API key status dynamically
        clearbit_status = "✅" if strategy_agent.research_agent.clearbit_api_key else "❌"
        apollo_status = "✅" if strategy_agent.research_agent.apollo_api_key else "❌"
        perplexity_status = "✅" if strategy_agent.research_agent.perplexity_api_key else "❌"
        
        recent_leads = "Example: research person: Dr. Sarah at Wellness Clinic"
        
        result = agent_menu_generator(
            agent_name="Research Agent",
            agent_capabilities=f"{capabilities}\n\nStatus: Clearbit {clearbit_status}, Apollo {apollo_status}, Perplexity {perplexity_status}",
            user_context=text,
            recent_leads=recent_leads
        )
        
        # Format menu with suggested command and example
        response = f"🔍 {result.menu_text}"
        if result.suggested_command:
            response += f"\n\n**Try this:** `{result.suggested_command}`"
        if result.example_usage:
            response += f"\n\n**Example:**\n```\n{result.example_usage}\n```"
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating research agent menu: {e}")
        return "🔍 Research Agent menu temporarily unavailable. Try asking: 'research [person/company]'"


async def call_inbound_agent(text: str) -> str:
    """Call the Inbound Agent - DSPy generates contextual menu.
    
    Args:
        text: Original message text (user context)
    
    Returns:
        DSPy-generated menu with capabilities
    """
    if not agent_menu_generator:
        return "❌ Agent menu generator not configured"
    
    try:
        capabilities = """Lead qualification (DSPy-powered), Scoring explanations, 
Pipeline analysis, Requalification, Test qualification logic"""
        
        recent_leads = "Recent: 3 HOT, 7 WARM, 10 COOL leads qualified today"
        
        result = agent_menu_generator(
            agent_name="Inbound Agent",
            agent_capabilities=capabilities,
            user_context=text,
            recent_leads=recent_leads
        )
        
        response = f"📥 {result.menu_text}"
        if result.suggested_command:
            response += f"\n\n**Try this:** `{result.suggested_command}`"
        if result.example_usage:
            response += f"\n\n**Example:**\n```\n{result.example_usage}\n```"
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating inbound agent menu: {e}")
        return "📥 Inbound Agent menu temporarily unavailable. Try asking: 'show recent leads'"


async def call_followup_agent(text: str) -> str:
    """Call the Follow-Up Agent - DSPy generates contextual menu.
    
    Args:
        text: Original message text (user context)
    
    Returns:
        DSPy-generated menu with capabilities
    """
    if not agent_menu_generator:
        return "❌ Agent menu generator not configured"
    
    try:
        capabilities = """Follow-up email sequences (GMass), Sequence state tracking, 
Pause/resume sequences, Escalate to human, 8-stage tier-based campaigns"""
        
        recent_leads = "Active: 15 HOT sequences, 23 WARM sequences, next send in 2 hours"
        
        result = agent_menu_generator(
            agent_name="Follow-Up Agent",
            agent_capabilities=capabilities,
            user_context=text,
            recent_leads=recent_leads
        )
        
        response = f"📧 {result.menu_text}"
        if result.suggested_command:
            response += f"\n\n**Try this:** `{result.suggested_command}`"
        if result.example_usage:
            response += f"\n\n**Example:**\n```\n{result.example_usage}\n```"
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating follow-up agent menu: {e}")
        return "📧 Follow-Up Agent menu temporarily unavailable. Try asking: 'show followup status'"


# ============================================================================
# QUICK COMMANDS
# ============================================================================

async def quick_pipeline_status() -> str:
    """Get quick pipeline status - DSPy generates contextual summary.
    
    Returns:
        DSPy-generated pipeline summary
    """
    if not pipeline_status:
        return "❌ Pipeline status generator not configured"
    
    try:
        # TODO: Query real Supabase data
        pipeline_counts = """HOT: 3 leads, WARM: 8 leads, COOL: 12 leads, COLD: 5 leads"""
        today_activity = """Today: 4 new leads qualified, 2 moved to HOT, 6 follow-up emails sent"""
        urgent_items = """1 HOT lead needs call today (booked Calendly)"""
        
        result = pipeline_status(
            pipeline_counts=pipeline_counts,
            today_activity=today_activity,
            urgent_items=urgent_items
        )
        
        response = f"📊 **Pipeline Status**\n\n{result.status_summary}"
        if result.action_needed:
            response += f"\n\n⚠️ **Action Needed:**\n{result.action_needed}"
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating pipeline status: {e}")
        return "📊 Pipeline status temporarily unavailable. Try asking: 'how many leads do we have?'"


async def quick_research_lead(text: str) -> str:
    """Extract lead info from text and trigger research.
    
    Args:
        text: Message containing lead info
    
    Returns:
        Research status message
    """
    # Try to extract lead ID
    import re
    lead_id_match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', text)
    
    if lead_id_match:
        lead_id = lead_id_match.group(0)
        
        # Trigger research via A2A
        response = await strategy_agent._a2a_command(
            agent_type="research",
            action="research_lead_deeply",
            lead_id=lead_id
        )
        
        task_id = response.get("task_id")
        return f"""🔍 **Research Task Started**

Lead: `{lead_id}`
Task ID: `{task_id}`

I'll notify you when research is complete!

_Researching:_
• Person profile (Clearbit, LinkedIn)
• Company intelligence
• Additional contacts
• Engagement strategy

⏱️ ETA: ~30 seconds
"""
    
    else:
        return """❌ **No lead ID found**

Please provide a lead ID in format:
`research lead: abc-123-def-456`

Or use:
`research person: [name] at [company]`
"""


def get_available_agents(user_question: str = "") -> str:
    """List all available agents - DSPy generates contextual list.
    
    Args:
        user_question: What user asked (for context)
    
    Returns:
        DSPy-generated agents overview
    """
    if not agents_lister:
        return "❌ Agents lister not configured"
    
    try:
        # Build system state dynamically
        system_state = f"""All 4 agents operational. 
Recent activity: 12 leads qualified, 3 research tasks, 8 follow-up emails sent today.
Strategy Agent (current): Active and responding."""
        
        result = agents_lister(
            system_state=system_state,
            user_question=user_question
        )
        
        response = f"🤖 {result.agents_overview}"
        if result.which_agent_to_use:
            response += f"\n\n💡 **Guidance:**\n{result.which_agent_to_use}"
        
        return response
    
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return "🤖 Available agents: Research, Inbound, Follow-Up, Strategy. Try 'call [agent name]'"


def get_help_message(user_message: str = "", user_history: str = "") -> str:
    """Get help message - DSPy generates contextual help.
    
    Args:
        user_message: What user just asked
        user_history: User's previous commands (for context)
    
    Returns:
        DSPy-generated contextual help
    """
    if not help_generator:
        return "❌ Help generator not configured"
    
    try:
        available_agents = "Research Agent, Inbound Agent, Follow-Up Agent, Strategy Agent"
        available_commands = """call [agent], pipeline status, research lead: [id], 
list agents, show recent leads, natural language questions"""
        
        result = help_generator(
            user_message=user_message or "help",
            available_agents=available_agents,
            user_history=user_history or "No previous commands"
        )
        
        response = f"🎯 {result.help_message}"
        if result.suggested_first_step:
            response += f"\n\n**Try this first:** `{result.suggested_first_step}`"
        
        return response
    
    except Exception as e:
        logger.error(f"Error generating help: {e}")
        return "🎯 Try: 'call research agent', 'pipeline status', 'list agents', or just ask me anything!"


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ['router', 'handle_message', 'route_command']
