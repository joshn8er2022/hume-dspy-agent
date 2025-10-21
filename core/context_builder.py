
"""Dynamic Context Builder for Token Optimization.

Provides different context levels based on message complexity:
- Minimal: ~30 tokens (simple messages)
- Pipeline: ~100 tokens (pipeline queries)
- Full: ~800 tokens (complex analysis)
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build appropriate context based on message needs."""

    def __init__(self, supabase_client=None):
        """Initialize context builder.

        Args:
            supabase_client: Optional Supabase client for real-time data
        """
        self.supabase = supabase_client

    def get_minimal_context(self) -> str:
        """Get minimal context for simple messages.

        Returns ~30 tokens - just enough for agent to know it's operational.

        Returns:
            JSON string with minimal context
        """
        context = {
            "status": "operational",
            "agents": ["inbound", "research", "follow_up", "strategy"],
            "system": "Hume AI B2B Sales Automation"
        }
        return json.dumps(context)

    def get_pipeline_context(self) -> str:
        """Get pipeline data context for lead/stats queries.

        Returns ~100 tokens - includes lead distribution.

        Returns:
            JSON string with pipeline context
        """
        # Try to get real-time data from Supabase
        pipeline_data = self._get_pipeline_data()

        context = {
            "status": "operational",
            "system": "Hume AI B2B Sales Automation",
            "pipeline": pipeline_data
        }
        return json.dumps(context, indent=2)

    def get_full_context(
        self,
        include_infrastructure: bool = True,
        include_integrations: bool = True,
        include_pipeline: bool = True
    ) -> str:
        """Get full context for complex analysis.

        Returns ~800 tokens - complete system information.

        Args:
            include_infrastructure: Include infrastructure details
            include_integrations: Include integration status
            include_pipeline: Include pipeline data

        Returns:
            JSON string with full context
        """
        context = {}

        if include_infrastructure:
            context["infrastructure"] = self._get_infrastructure_context()

        if include_pipeline:
            context["current_state"] = self._get_pipeline_data()

        if include_integrations:
            context["integrations"] = self._get_integrations_status()

        context["tech_stack"] = {
            "ai_framework": "DSPy (ChainOfThought, ReAct modules)",
            "validation": "Pydantic BaseModel",
            "orchestration": "LangGraph",
            "llm": "Claude (Haiku/Sonnet via OpenRouter)"
        }

        return json.dumps(context, indent=2)

    def _get_pipeline_data(self) -> Dict[str, Any]:
        """Get current pipeline data from Supabase.

        Returns:
            Pipeline data dict or error state
        """
        if not self.supabase:
            return {
                "data_access": "UNAVAILABLE",
                "message": "Supabase not configured"
            }

        try:
            # Query leads by tier
            response = self.supabase.table("leads").select("tier").execute()

            if response.data:
                # Count by tier
                tier_counts = {"HOT": 0, "WARM": 0, "COOL": 0, "COLD": 0, "UNQUALIFIED": 0}
                for lead in response.data:
                    tier = lead.get("tier", "UNQUALIFIED").upper()
                    if tier in tier_counts:
                        tier_counts[tier] += 1

                return {
                    "data_access": "LIVE",
                    "leads_by_tier": tier_counts,
                    "total_leads": len(response.data),
                    "data_source": "Supabase (real-time)"
                }
            else:
                return {
                    "data_access": "EMPTY",
                    "total_leads": 0,
                    "message": "No leads in database"
                }

        except Exception as e:
            logger.error(f"Error fetching pipeline data: {e}")
            return {
                "data_access": "ERROR",
                "error": str(e),
                "message": "Database query failed"
            }

    def _get_infrastructure_context(self) -> Dict[str, Any]:
        """Get infrastructure context (entry points, agents, etc.).

        Returns:
            Infrastructure context dict
        """
        return {
            "entry_points": [
                {"path": "/webhooks/typeform", "purpose": "Lead capture"},
                {"path": "/webhooks/vapi", "purpose": "Voice AI calls"},
                {"path": "/slack/events", "purpose": "Slack bot"},
                {"path": "/a2a/introspect", "purpose": "Agent-to-agent"}
            ],
            "agents": {
                "inbound": "Lead qualification (DSPy + Sonnet)",
                "research": "Intelligence gathering (Perplexity, Apollo)",
                "follow_up": "Email sequences (GMass, LangGraph)",
                "strategy": "Strategic execution (YOU - Josh's AI partner)"
            }
        }

    def _get_integrations_status(self) -> Dict[str, str]:
        """Get integration status.

        Returns:
            Integration status dict
        """
        return {
            "slack": "✅",
            "gmass": "Email campaigns",
            "close_crm": "Lead sync",
            "supabase": "✅ Live data",
            "mcp_zapier": "✅ 200+ tools",
            "mcp_perplexity": "AI research"
        }


# Global singleton
_context_builder = None

def get_context_builder(supabase_client=None) -> ContextBuilder:
    """Get or create global ContextBuilder instance."""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder(supabase_client)
    return _context_builder


def build_context(
    message: str,
    supabase_client=None,
    force_full: bool = False
) -> str:
    """Build appropriate context based on message.

    Args:
        message: User message to analyze
        supabase_client: Optional Supabase client
        force_full: Force full context regardless of message

    Returns:
        JSON context string
    """
    from core.message_classifier import classify_message, needs_full_context, needs_pipeline_data

    builder = get_context_builder(supabase_client)

    # Force full context if requested
    if force_full:
        return builder.get_full_context()

    # Check if message explicitly needs full context
    if needs_full_context(message):
        return builder.get_full_context()

    # Check if message needs pipeline data
    if needs_pipeline_data(message):
        return builder.get_pipeline_context()

    # Check message complexity
    complexity = classify_message(message)

    if complexity == "simple":
        return builder.get_minimal_context()
    else:
        return builder.get_full_context()
