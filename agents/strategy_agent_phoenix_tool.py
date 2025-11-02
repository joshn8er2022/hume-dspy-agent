"""Phoenix MCP Tool Integration for StrategyAgent.

Enables StrategyAgent to query Phoenix traces directly via MCP.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def analyze_phoenix_traces_for_development(
    project_name: str = "hume-dspy-agent",
    span_limit: int = 100,
    hours_back: int = 24
) -> Dict[str, Any]:
    """Query Phoenix via MCP to analyze recent system behavior.
    
    This function uses Phoenix MCP tools to:
    1. Fetch recent spans
    2. Analyze for development patterns
    3. Identify system levers
    
    Args:
        project_name: Phoenix project name
        span_limit: Max spans to analyze
        hours_back: Hours to look back
        
    Returns:
        Analysis dict with insights and levers
    """
    logger.info(f"🔍 Querying Phoenix MCP for development analysis...")
    logger.info(f"   Project: {project_name}")
    logger.info(f"   Spans: {span_limit}")
    logger.info(f"   Time window: {hours_back} hours")
    
    try:
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Import Phoenix introspection module
        from agents.development_introspection import (
            DevelopmentIntrospection,
            get_phoenix_spans_via_mcp
        )
        
        introspection = DevelopmentIntrospection(project_name)
        
        # Get spans via MCP (this will use mcp_phoenix_get-spans when MCP tools are available)
        spans = await get_phoenix_spans_via_mcp(
            project_name=project_name,
            limit=span_limit,
            hours_back=hours_back
        )
        
        if not spans:
            logger.warning("⚠️ No spans retrieved from Phoenix - MCP may not be available")
            return {
                "error": "No spans available",
                "message": "Phoenix MCP tools may not be accessible. Check MCP configuration.",
                "spans_analyzed": 0
            }
        
        # Analyze spans
        insights = introspection.detect_development_needs(spans)
        levers = introspection.identify_system_levers(spans)
        
        # Calculate summary stats
        error_spans = [s for s in spans if s.get("attributes", {}).get("@level") == "error"]
        latencies = [
            (s.get("end_time_ns", 0) - s.get("start_time_ns", 0)) / 1_000_000
            for s in spans if s.get("end_time_ns") and s.get("start_time_ns")
        ]
        
        summary = {
            "spans_analyzed": len(spans),
            "time_window_hours": hours_back,
            "error_rate": len(error_spans) / len(spans) if spans else 0,
            "error_count": len(error_spans),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        }
        
        analysis = {
            "insights": [i.model_dump() for i in insights],
            "levers": [l.model_dump() for l in levers],
            "summary": summary,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
        
        # Format message for developer communication
        formatted_message = introspection.format_for_developer_communication(analysis)
        analysis["formatted_message"] = formatted_message
        
        logger.info(f"✅ Analysis complete: {len(insights)} insights, {len(levers)} levers")
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Phoenix trace analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "message": "Failed to analyze Phoenix traces",
            "spans_analyzed": 0
        }

