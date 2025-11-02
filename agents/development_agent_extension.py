"""Development Agent Extension - Enables StrategyAgent to request developer help.

This extension hooks into StrategyAgent's execution to:
1. Monitor for development/debugging patterns
2. Query Phoenix traces when needed
3. Generate development insights
4. Communicate findings to developers
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from agents.base_agent import AgentExtension
from agents.development_introspection import (
    DevelopmentIntrospection,
    get_phoenix_spans_via_mcp
)

logger = logging.getLogger(__name__)


class DevelopmentAgentExtension(AgentExtension):
    """Extension that enables StrategyAgent to introspect and request developer help."""
    
    def __init__(self, phoenix_project_name: str = "hume-dspy-agent", agent=None):
        super().__init__("DevelopmentIntrospection")
        self.introspection = DevelopmentIntrospection(phoenix_project_name)
        self.agent = agent  # Reference to StrategyAgent for MCP client access
        self.last_analysis = None
        self.analysis_interval_hours = 6  # Analyze every 6 hours
    
    def set_agent(self, agent):
        """Set the agent reference after registration."""
        self.agent = agent
    
    async def on_error(
        self,
        task: str,
        error: Exception = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """When an error occurs, check if we should analyze Phoenix traces."""
        
        # Check if this is a development/debugging scenario
        should_analyze = self._should_trigger_analysis(error, task)
        
        if should_analyze:
            logger.info("🔍 Development trigger detected - analyzing Phoenix traces...")
            
            try:
                # Get MCP client from agent if available
                mcp_client = None
                if self.agent and hasattr(self.agent, 'mcp_client'):
                    mcp_client = self.agent.mcp_client
                
                # Get recent spans
                spans = await get_phoenix_spans_via_mcp(
                    project_name=self.introspection.phoenix_project,
                    limit=100,
                    hours_back=24,
                    mcp_client=mcp_client
                )
                
                if spans:
                    # Analyze spans for development needs
                    insights = self.introspection.detect_development_needs(spans)
                    levers = self.introspection.identify_system_levers(spans)
                    
                    # Extract business evolution signals (NEW)
                    business_signals = self.introspection.extract_business_evolution_signals(spans)
                    
                    # Generate analysis
                    analysis = {
                        "insights": [i.model_dump() for i in insights],
                        "levers": [l.model_dump() for l in levers],
                        "business_signals": business_signals,  # NEW: Business evolution data
                        "summary": {
                            "spans_analyzed": len(spans),
                            "error_rate": len([s for s in spans if s.get("attributes", {}).get("@level") == "error"]) / len(spans) if spans else 0,
                            "triggered_by": str(error) if error else "development_request",
                            "task": task
                        }
                    }
                    
                    # Format for communication
                    message = self.introspection.format_for_developer_communication(analysis)
                    
                    # Return for StrategyAgent to communicate
                    return {
                        "development_insight": True,
                        "analysis": analysis,
                        "formatted_message": message,
                        "should_notify_developer": len(insights) > 0,
                        "insight_count": len(insights),
                        "lever_count": len(levers)
                    }
            
            except Exception as e:
                logger.error(f"❌ Failed to analyze Phoenix traces: {e}")
        
        return None
    
    async def after_execute(
        self,
        task: str,
        result: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """After execution, check if periodic analysis is needed."""
        
        # Check if it's time for periodic analysis
        if self._should_run_periodic_analysis():
            logger.info("⏰ Periodic development analysis triggered...")
            
            try:
                # Get MCP client from agent if available
                mcp_client = None
                if self.agent and hasattr(self.agent, 'mcp_client'):
                    mcp_client = self.agent.mcp_client
                
                analysis = await self.introspection.analyze_recent_behavior(
                    span_limit=100,
                    time_window_hours=24,
                    mcp_client=mcp_client
                )
                
                self.last_analysis = datetime.utcnow()
                
                # If insights found, mark for developer notification
                if analysis.get("insights"):
                    result["development_analysis"] = analysis
                    result["development_notification_needed"] = True
            
            except Exception as e:
                logger.error(f"❌ Periodic analysis failed: {e}")
        
        return result
    
    def _should_trigger_analysis(self, error: Exception, task: str) -> bool:
        """Determine if an error should trigger Phoenix trace analysis."""
        
        # Trigger on:
        # 1. Repeated errors (pattern detection)
        # 2. New error types
        # 3. Critical errors
        # 4. Performance-related errors
        
        error_str = str(error).lower()
        task_str = task.lower()
        
        # Critical keywords
        critical_keywords = [
            "timeout", "connection", "database", "api", "rate limit",
            "memory", "error", "exception", "failed"
        ]
        
        # Development-related tasks
        dev_keywords = [
            "debug", "analyze", "investigate", "monitor", "performance",
            "optimize", "fix", "issue"
        ]
        
        has_critical_keyword = any(kw in error_str or kw in task_str for kw in critical_keywords)
        has_dev_keyword = any(kw in task_str for kw in dev_keywords)
        
        return has_critical_keyword or has_dev_keyword
    
    def _should_run_periodic_analysis(self) -> bool:
        """Check if periodic analysis should run."""
        if self.last_analysis is None:
            return True
        
        hours_since_analysis = (datetime.utcnow() - self.last_analysis).total_seconds() / 3600
        return hours_since_analysis >= self.analysis_interval_hours


# Integration with StrategyAgent
def enable_development_introspection(agent) -> DevelopmentAgentExtension:
    """Enable development introspection for an agent."""
    extension = DevelopmentAgentExtension()
    if hasattr(agent, 'add_extension'):
        agent.add_extension(extension)
    elif hasattr(agent, 'extensions'):
        agent.extensions.append(extension)
    logger.info("✅ Development introspection extension enabled")
    return extension

