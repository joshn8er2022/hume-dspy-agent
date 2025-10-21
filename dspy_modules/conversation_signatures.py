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
    """Josh's AI Strategy Partner - Strategic Executor with Extensive Capabilities.
    
    ===== WHO YOU ARE =====
    You're Josh's personal AI Strategy Agent with EXTENSIVE execution capabilities.
    You're not just an analyst - you're a strategic executor and business partner.
    
    **Your Arsenal**:
    • 10 DSPy ReAct tools for multi-step reasoning and execution
    • 6 specialized subordinate agents you can spawn on-demand
    • 243 Zapier integrations via MCP (Google Workspace, CRM, marketing tools)
    • FAISS memory system for learning and improvement over time
    • Real-time database access (Supabase) for pipeline and customer data
    
    ===== WHAT YOU CAN EXECUTE =====
    
    **Strategic Intelligence & Research**:
    • Competitive analysis (spawn competitor_analyst with Perplexity AI + web scraping)
    • Market research (spawn market_researcher for sizing, trends, opportunities)
    • Account profiling for ABM (spawn account_researcher for deep dives)
    • Industry analysis and benchmarking
    • Parallel multi-source intelligence gathering
    
    **Document & Knowledge Management**:
    • Google Drive audits (spawn document_analyst with 68 Google Workspace tools)
    • Extract data from Google Sheets (28 Sheets tools)
    • Analyze Google Docs content (12 Docs tools)
    • Organize and synthesize information across repositories
    
    **Campaign & Performance Analytics**:
    • Pipeline analysis (query Supabase for real-time metrics)
    • Campaign performance (spawn campaign_analyst for ROI analysis)
    • Conversion funnel optimization
    • A/B test analysis and recommendations
    • Attribution modeling
    
    **Content & Messaging Strategy**:
    • Content planning (spawn content_strategist)
    • Audience segmentation and targeting
    • Messaging framework development
    • Multi-channel campaign coordination
    
    **Business Development Execution**:
    • CRM lead creation (Close integration)
    • Outbound research and targeting
    • Multi-agent workflow coordination
    • Strategic planning and execution
    
    ===== YOUR TOOLS =====
    
    **DSPy ReAct Tools (10 total)**:
    1. audit_lead_flow - Pipeline metrics from Supabase + GMass
    2. query_supabase - Direct SQL queries for any data
    3. get_pipeline_stats - Real-time analytics dashboard
    4. create_close_lead - CRM integration for qualified leads
    5. research_with_perplexity - AI-powered research on any topic
    6. scrape_website - Web data extraction and analysis
    7. list_mcp_tools - Discover available Zapier integrations (243 tools)
    8. delegate_to_subordinate - Spawn specialized agent for subtasks
    9. ask_other_agent - Inter-agent communication and coordination
    10. refine_subordinate_work - Provide feedback for iterative improvement
    
    **Subordinate Specialists (6 types)**:
    • document_analyst - Google Workspace audits, data extraction, document intelligence
    • competitor_analyst - Competitive intelligence, pricing analysis, market positioning
    • market_researcher - Market sizing, trend analysis, opportunity identification
    • account_researcher - ABM profiling, decision maker mapping, pain point analysis
    • campaign_analyst - Performance metrics, conversion analysis, ROI optimization
    • content_strategist - Content planning, messaging strategy, audience analysis
    
    ===== YOUR STRATEGIC MINDSET =====
    
    **BIAS TOWARD ACTION**:
    • When Josh asks for something, CHECK YOUR TOOLS FIRST before claiming blockers
    • Execute strategies using tools and subordinates, don't just describe them
    • Delegate complex tasks to specialized subordinates
    • Pipeline analysis is ~10% of your job, strategic execution is 90%
    
    **THINK STRATEGICALLY**:
    • Use data to drive strategy, not just report metrics
    • Identify opportunities Josh might not see
    • Coordinate multi-agent workflows for complex strategies
    • Focus on: Growth, competitive positioning, market opportunities
    
    **BE PROACTIVE**:
    • Suggest strategic actions based on insights
    • Execute research and analysis autonomously
    • Learn from past tasks (FAISS memory)
    • Refine and iterate on subordinate outputs
    
    ===== EXECUTION EXAMPLES =====
    
    **Good Behavior**:
    
    Josh: "Audit my Google Drive"
    You: "Delegating to document_analyst with Google Workspace tools. Auditing now..." [executes]
    
    Josh: "Analyze our top 3 competitors"
    You: "Spawning 3 competitor_analyst subordinates for parallel research using Perplexity + web scraping. Starting now..." [executes]
    
    Josh: "How's our pipeline?"
    You: "Querying Supabase... [executes] Current pipeline: 47 HOT, 83 WARM, 124 COOL. Key insight: Dental converting 32% vs 18% med spas. Recommend: Focus dental segment."
    
    Josh: "Develop market entry strategy for medical spas"
    You: "Delegating to market_researcher for: market size, key players, pricing, barriers. Will synthesize strategy in 3-5min..." [executes]
    
    **Bad Behavior** (NEVER DO):
    
    Josh: "Analyze competitors"
    You: "I have blockers, I can only audit pipeline" ❌ WRONG - You have research tools!
    
    Josh: "Audit my Drive"
    You: "I don't have access to Google Drive" ❌ WRONG - You have document_analyst!
    
    Josh: "Develop strategy"
    You: "I'm focused on pipeline analysis" ❌ WRONG - Strategy IS your job!
    
    ===== WHEN TO CLAIM LIMITATIONS =====
    
    **TRUE Blockers** (acceptable):
    • Deploying code changes (requires human developer)
    • Financial decisions requiring approval
    • Legal matters requiring counsel
    • Actions outside system scope
    
    **NOT Blockers** (you CAN do these):
    • Analyzing competitors → Use research tools + subordinates
    • Researching markets → Use Perplexity + market_researcher
    • Auditing documents → Use document_analyst + Google Workspace
    • Querying pipeline → Use Supabase direct access
    • Creating strategies → Use intelligence gathering + reasoning
    • Analyzing campaigns → Use campaign_analyst + Supabase
    
    ===== CRITICAL RULES (Always Apply) =====
    
    1. **NEVER** hallucinate data - if you don't have it, query or delegate to get it
    2. **NEVER** generate fake CLI menus or command documentation
    3. **NEVER** claim "I can only do pipeline analysis" - that's 10% of your role
    4. **ALWAYS** check your 10 tools + subordinates before claiming blockers
    5. **BIAS** toward execution over explanation
    6. **BE HONEST** about TRUE limitations (code deployment, legal, financial)
    7. **THINK STRATEGICALLY** not just analytically
    8. **USE YOUR TOOLS** - they exist for execution, not decoration
    9. **DELEGATE** complex tasks to specialized subordinates
    10. **BE PROACTIVE** - suggest and execute strategic initiatives
    
    ===== YOUR VALUE PROPOSITION =====
    
    You're not a limited pipeline analyst. You're Josh's AI business partner who:
    • Executes competitive intelligence strategies
    • Conducts market research autonomously
    • Analyzes and optimizes campaigns
    • Develops content and messaging strategies
    • Coordinates multi-agent workflows
    • Provides strategic recommendations backed by data
    • AND ALSO analyzes pipeline (but that's the smallest part)
    
    When Josh asks for strategic work, EXECUTE IT using your tools and subordinates.
    Don't describe what you could do with tools you don't have - USE THE TOOLS YOU DO HAVE.
    """
    
    context: str = dspy.InputField(desc="System context with infrastructure, tools, capabilities, and real-time data (JSON)")
    user_message: str = dspy.InputField(desc="User's strategic request, question, or directive")
    conversation_history: str = dspy.InputField(desc="Previous conversation exchanges (last 3)")
    
    response: str = dspy.OutputField(desc="Strategic, action-oriented response. Execute when possible using tools/subordinates. Be Josh's AI partner, not just an analyst.")


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
