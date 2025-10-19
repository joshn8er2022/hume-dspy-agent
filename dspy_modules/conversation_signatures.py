"""DSPy signatures for conversational AI and Slack bot interactions.

ALL bot responses should go through these signatures - NO hardcoded strings!
This allows DSPy to optimize prompts and maintain consistency.
"""
import dspy
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# STRATEGY AGENT SIGNATURES
# ============================================================================

class StrategyConversation(dspy.Signature):
    """Conversational AI for Strategy Agent - BE HONEST about data access.
    
    You are Josh's personal AI Strategy Agent for Hume Health's B2B sales automation system.
    
    CRITICAL RULES:
    1. NEVER hallucinate data - if you don't have access to real-time metrics, SAY SO
    2. If context shows "Check Supabase" or "TODO", tell user you need database access first
    3. Be conversational and understand intent - NOT keyword-matching
    4. Suggest what you COULD do if given the right access/tools
    5. Be helpful and honest, not fake-knowledgeable
    
    You CAN help with:
    - Explaining system architecture and how things work
    - Discussing strategy and recommendations WHEN given actual data
    - Understanding what the user wants and routing to the right solution
    - Being transparent about limitations
    
    You CANNOT:
    - Provide real-time metrics without database access
    - Execute commands without proper tool integration
    - Make up pipeline numbers
    """
    
    context: str = dspy.InputField(desc="System context with ACTUAL data access status (JSON)")
    user_message: str = dspy.InputField(desc="User's question or request")
    conversation_history: str = dspy.InputField(desc="Previous conversation (last 3 exchanges)")
    
    response: str = dspy.OutputField(desc="Honest, conversational response - admit limitations, suggest solutions")


class PipelineAnalysis(dspy.Signature):
    """Analyze pipeline data and generate strategic insights.
    
    Analyze lead pipeline data and provide actionable insights.
    Focus on: conversion bottlenecks, tier distribution, source performance.
    """
    
    pipeline_data: str = dspy.InputField(desc="JSON string of pipeline metrics (leads by tier, source, time)")
    time_period: str = dspy.InputField(desc="Analysis period (e.g., 'last 7 days')")
    user_question: str = dspy.InputField(desc="Specific question user asked (if any)")
    
    summary: str = dspy.OutputField(desc="2-3 sentence executive summary")
    key_metrics: str = dspy.OutputField(desc="Bullet points of top 3-5 metrics with context")
    insights: str = dspy.OutputField(desc="2-3 strategic insights with reasoning")
    recommended_actions: str = dspy.OutputField(desc="3-5 specific action items, prioritized")


class GenerateRecommendations(dspy.Signature):
    """Generate strategic recommendations based on system state.
    
    Analyze current pipeline state, agent performance, and business context
    to provide prioritized recommendations.
    """
    
    pipeline_state: str = dspy.InputField(desc="Current pipeline metrics and trends")
    recent_activity: str = dspy.InputField(desc="Recent lead activity and agent actions")
    business_goals: str = dspy.InputField(desc="Hume Health's current priorities")
    
    recommendations: str = dspy.OutputField(desc="3-5 prioritized recommendations with impact/effort assessment")
    quick_wins: str = dspy.OutputField(desc="1-2 actions that can be done today")
    strategic_focus: str = dspy.OutputField(desc="One key area to focus on this week")


# ============================================================================
# SLACK BOT INTERFACE SIGNATURES
# ============================================================================

class GenerateHelpMessage(dspy.Signature):
    """Generate contextual help message for Slack user.
    
    Provide helpful, personalized guidance based on what the user just asked.
    Show relevant commands and examples.
    """
    
    user_message: str = dspy.InputField(desc="What the user just asked")
    available_agents: str = dspy.InputField(desc="List of available agents and their capabilities")
    user_history: str = dspy.InputField(desc="What this user has asked before (if any)")
    
    help_message: str = dspy.OutputField(desc="Formatted help text with commands and examples")
    suggested_first_step: str = dspy.OutputField(desc="Best command for this user to try first")


class GenerateAgentMenu(dspy.Signature):
    """Generate interactive menu for specific agent.
    
    Show agent capabilities and suggest relevant commands based on user context.
    """
    
    agent_name: str = dspy.InputField(desc="Agent being called (Research, Inbound, Follow-Up)")
    agent_capabilities: str = dspy.InputField(desc="Full list of agent capabilities")
    user_context: str = dspy.InputField(desc="Why user called this agent / what they're trying to do")
    recent_leads: str = dspy.InputField(desc="Recent leads this agent has worked on (for examples)")
    
    menu_text: str = dspy.OutputField(desc="Formatted menu with capabilities and examples")
    suggested_command: str = dspy.OutputField(desc="Most relevant command for this user's context")
    example_usage: str = dspy.OutputField(desc="Concrete example they can copy-paste")


class ListAgents(dspy.Signature):
    """Generate overview of all available agents.
    
    Provide clear, concise overview of each agent and when to use them.
    """
    
    system_state: str = dspy.InputField(desc="Current system state (agents online, recent activity)")
    user_question: str = dspy.InputField(desc="What user asked (if specific)")
    
    agents_overview: str = dspy.OutputField(desc="Formatted list of agents with descriptions")
    which_agent_to_use: str = dspy.OutputField(desc="Guidance on which agent to use for common tasks")


class ResearchTaskResponse(dspy.Signature):
    """Generate response for research task initiation.
    
    Confirm research task started and explain what will be researched.
    """
    
    task_type: str = dspy.InputField(desc="Type of research (person, company, lead)")
    target: str = dspy.InputField(desc="What is being researched")
    research_scope: str = dspy.InputField(desc="What data sources will be used")
    
    confirmation_message: str = dspy.OutputField(desc="Formatted confirmation with ETA")
    what_to_expect: str = dspy.OutputField(desc="What insights user will receive")


class QuickPipelineStatus(dspy.Signature):
    """Generate quick pipeline status summary for Slack.
    
    Provide at-a-glance pipeline health for busy founder.
    """
    
    pipeline_counts: str = dspy.InputField(desc="Lead counts by tier (HOT, WARM, COOL, COLD)")
    today_activity: str = dspy.InputField(desc="Today's new leads and agent actions")
    urgent_items: str = dspy.InputField(desc="Anything requiring immediate attention")
    
    status_summary: str = dspy.OutputField(desc="2-3 line status with key numbers")
    action_needed: str = dspy.OutputField(desc="What Josh should focus on today (if anything urgent)")


# ============================================================================
# FOLLOW-UP AGENT SIGNATURES
# ============================================================================

class FollowUpStatus(dspy.Signature):
    """Generate follow-up sequence status for a lead.
    
    Explain current follow-up state and next actions clearly.
    """
    
    lead_data: str = dspy.InputField(desc="Lead info (name, company, tier)")
    follow_up_state: str = dspy.InputField(desc="Current sequence state (stage, emails sent, last contact)")
    engagement_signals: str = dspy.InputField(desc="Email opens, clicks, replies")
    
    status_message: str = dspy.OutputField(desc="Clear status summary with timeline")
    engagement_analysis: str = dspy.OutputField(desc="Assessment of lead engagement")
    recommended_action: str = dspy.OutputField(desc="What to do next (continue, pause, escalate)")


# ============================================================================
# ERROR & FALLBACK SIGNATURES
# ============================================================================

class HandleUnknownCommand(dspy.Signature):
    """Handle unrecognized command gracefully.
    
    Figure out what user was trying to do and guide them to the right command.
    """
    
    user_input: str = dspy.InputField(desc="What the user typed")
    available_commands: str = dspy.InputField(desc="All available commands")
    
    interpretation: str = dspy.OutputField(desc="What you think the user wanted")
    suggested_command: str = dspy.OutputField(desc="The correct command to use")
    helpful_response: str = dspy.OutputField(desc="Friendly response with guidance")


class ExplainError(dspy.Signature):
    """Explain error in user-friendly way.
    
    Translate technical errors into plain language and suggest fixes.
    """
    
    error_message: str = dspy.InputField(desc="Technical error message")
    user_action: str = dspy.InputField(desc="What the user was trying to do")
    
    plain_english_explanation: str = dspy.OutputField(desc="What went wrong in simple terms")
    how_to_fix: str = dspy.OutputField(desc="Specific steps to resolve")
    alternative_approach: str = dspy.OutputField(desc="Different way to accomplish same goal (if applicable)")


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    # Strategy Agent
    "StrategyConversation",
    "PipelineAnalysis",
    "GenerateRecommendations",
    
    # Slack Interface
    "GenerateHelpMessage",
    "GenerateAgentMenu",
    "ListAgents",
    "ResearchTaskResponse",
    "QuickPipelineStatus",
    
    # Follow-Up Agent
    "FollowUpStatus",
    
    # Error Handling
    "HandleUnknownCommand",
    "ExplainError",
]
