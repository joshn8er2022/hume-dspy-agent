"""Slack Bot for Personal Agent Communication.

This bot allows Josh to interact with all agents via Slack DM:
- Call specific agents ("call research agent")
- Query agent state ("show inbound status")
- Issue commands ("research lead abc-123")
- Get strategic insights ("what should I focus on?")
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
import httpx

from agents.strategy_agent import StrategyAgent
from agents.introspection import get_introspection_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/slack", tags=["slack"])

# Initialize Strategy Agent (handles all agent coordination)
strategy_agent = StrategyAgent()


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
                await handle_message(event)
            
            return {"ok": True}
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"❌ Slack event error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


async def handle_message(event: Dict[str, Any]):
    """Process incoming Slack message.
    
    Args:
        event: Slack event data containing message info
    """
    try:
        text = event.get("text", "").strip()
        user = event.get("user")
        channel = event.get("channel")
        ts = event.get("ts")
        
        # Remove bot mention if present
        text = text.replace("<@U0935UUHRC7>", "").strip()  # Bot user ID
        
        logger.info(f"💬 Slack message from {user}: {text[:100]}...")
        
        # Parse command and route to appropriate handler
        response = await route_command(text, user)
        
        # Send response to Slack
        await strategy_agent.send_slack_message(
            message=response,
            channel=channel,
            thread_ts=ts
        )
    
    except Exception as e:
        logger.error(f"❌ Message handling error: {str(e)}")
        await strategy_agent.send_slack_message(
            message=f"❌ Error: {str(e)}",
            channel=event.get("channel")
        )


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
        return get_available_agents()
    
    # Help
    elif any(word in text_lower for word in ["help", "what can you do", "commands"]):
        return get_help_message()
    
    # ===== DEFAULT: Strategy Agent Conversational =====
    else:
        return await strategy_agent.chat_with_josh(text)


# ============================================================================
# AGENT CALLERS
# ============================================================================

async def call_research_agent(text: str) -> str:
    """Call the Research Agent and return interactive menu.
    
    Args:
        text: Original message text
    
    Returns:
        Formatted response with Research Agent capabilities
    """
    # Get research agent capabilities via A2A
    introspection = get_introspection_service()
    
    result = introspection.handle_query({
        "mode": "query",
        "agent_type": "research",
        "action": "show_capabilities"
    })
    
    return f"""🔍 **Research Agent - Connected**

**Available Commands:**

1️⃣ **Research Person**
   `research person: John Smith at Big Clinic`
   
2️⃣ **Research Company**
   `research company: Wellness Clinic Inc`
   
3️⃣ **Find Contacts**
   `find contacts at: Big Medical Group`
   
4️⃣ **Deep Lead Research**
   `research lead: abc-123-def-456`

**Example:**
```
research person: Dr. Sarah Johnson at Wellness First
```

**Status:**
• Clearbit: {'✅' if strategy_agent.research_agent.clearbit_api_key else '❌ Not configured'}
• Apollo: {'✅' if strategy_agent.research_agent.apollo_api_key else '❌ Not configured'}
• Perplexity: {'✅' if strategy_agent.research_agent.perplexity_api_key else '❌ Not configured'}

_What would you like to research?_
"""


async def call_inbound_agent(text: str) -> str:
    """Call the Inbound Agent and show qualification stats.
    
    Args:
        text: Original message text
    
    Returns:
        Formatted response with Inbound Agent status
    """
    return f"""📥 **Inbound Agent - Connected**

**Available Commands:**

1️⃣ **Show Recent Qualifications**
   `show recent leads`
   
2️⃣ **Explain Score**
   `explain score for lead: abc-123`
   
3️⃣ **Requalify Lead**
   `requalify lead: abc-123`
   
4️⃣ **Test Qualification**
   `test qualification: [paste lead data]`

**Today's Activity:**
• Total Leads: [query Supabase]
• HOT: [count]
• WARM: [count]
• COLD: [count]

**Example:**
```
show recent leads
```

_What would you like to check?_
"""


async def call_followup_agent(text: str) -> str:
    """Call the Follow-Up Agent and show sequence status.
    
    Args:
        text: Original message text
    
    Returns:
        Formatted response with Follow-Up Agent status
    """
    return f"""📧 **Follow-Up Agent - Connected**

**Available Commands:**

1️⃣ **Show Follow-Up State**
   `show followup for lead: abc-123`
   
2️⃣ **Trigger Immediate Follow-Up**
   `send followup now to: abc-123`
   
3️⃣ **Pause Follow-Up**
   `pause followup for: abc-123`
   
4️⃣ **Escalate to Human**
   `escalate lead: abc-123`

**Active Sequences:**
• HOT leads: [count] active
• WARM leads: [count] active
• Next scheduled: [time]

**Example:**
```
show followup for lead: abc-123-def-456
```

_What would you like to do?_
"""


# ============================================================================
# QUICK COMMANDS
# ============================================================================

async def quick_pipeline_status() -> str:
    """Get quick pipeline status."""
    analysis = await strategy_agent.analyze_pipeline(days=7)
    return strategy_agent._format_pipeline_analysis(analysis)


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


def get_available_agents() -> str:
    """List all available agents."""
    return """🤖 **Available Agents**

1️⃣ **Research Agent** 🔍
   • Person/company research
   • Contact discovery
   • Competitive intelligence
   _Call with: `call research agent`_

2️⃣ **Inbound Agent** 📥
   • Lead qualification
   • Scoring explanations
   • Pipeline analysis
   _Call with: `call inbound agent`_

3️⃣ **Follow-Up Agent** 📧
   • Email sequences
   • Follow-up state tracking
   • Escalations
   _Call with: `call follow-up agent`_

4️⃣ **Strategy Agent** 🎯 _(You're talking to me!)_
   • Pipeline insights
   • Recommendations
   • Agent coordination

**Quick Commands:**
• `pipeline status`
• `research lead: [id]`
• `help`
"""


def get_help_message() -> str:
    """Get help message."""
    return """🎯 **Slack Agent Interface - Help**

**Call Agents:**
• `call research agent` - Connect to Research Agent
• `call inbound agent` - Connect to Inbound Agent
• `call follow-up agent` - Connect to Follow-Up Agent

**Quick Commands:**
• `pipeline status` - Show current pipeline
• `research lead: abc-123` - Research a lead
• `list agents` - Show all agents

**Natural Language:**
Just talk to me! I understand:
• "How many HOT leads do we have?"
• "Research John Smith at Big Clinic"
• "What should I focus on today?"

**Examples:**
```
call research agent
research lead: abc-123-def-456
show pipeline status
what are my top priorities?
```

_Try any command to get started!_
"""


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ['router', 'handle_message', 'route_command']
