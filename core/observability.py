"""Phoenix Observability Setup for DSPy Agents.

This MUST be imported BEFORE any DSPy or agent code executes.

Phoenix provides:
- Complete visibility into DSPy calls
- LLM token usage tracking
- Latency monitoring
- Error tracking
- Trace visualization at https://app.phoenix.arize.com/

Environment Variables Required:
- PHOENIX_API_KEY: Your Phoenix API key (from Settings)
- PHOENIX_PROJECT_NAME: Project name (default: "hume-dspy-agent")
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def initialize_phoenix_tracing() -> Optional[object]:
    """Initialize Phoenix tracing for DSPy instrumentation.
    
    This sets up OpenTelemetry tracing to send all DSPy calls,
    LLM interactions, and agent activities to Phoenix for observability.
    
    Returns:
        TracerProvider instance or None if not configured
    """
    
    phoenix_api_key = os.getenv("PHOENIX_API_KEY")
    phoenix_project = os.getenv("PHOENIX_PROJECT_NAME", "hume-dspy-agent")
    phoenix_endpoint = os.getenv(
        "PHOENIX_ENDPOINT",
        "https://app.phoenix.arize.com/s/buildoutinc/v1/traces"
    )
    
    if not phoenix_api_key:
        logger.warning("⚠️ PHOENIX_API_KEY not set - observability disabled")
        logger.warning("   Set PHOENIX_API_KEY in Railway environment to enable tracing")
        return None
    
    try:
        from phoenix.otel import register
        
        # Register Phoenix tracing BEFORE any DSPy code runs
        tracer_provider = register(
            project_name=phoenix_project,
            endpoint=phoenix_endpoint,
            auto_instrument=True  # Automatically instrument common libraries
        )
        
        logger.info("✅ Phoenix tracing initialized")
        logger.info(f"   Project: {phoenix_project}")
        logger.info(f"   Endpoint: {phoenix_endpoint}")
        logger.info(f"   Dashboard: https://app.phoenix.arize.com/")
        
        # Now instrument DSPy specifically
        try:
            from openinference.instrumentation.dspy import DSPyInstrumentor
            
            DSPyInstrumentor().instrument()
            logger.info("✅ DSPy instrumentation enabled")
            logger.info("   All DSPy calls will be traced in Phoenix")
        
        except ImportError:
            logger.warning("⚠️ openinference-instrumentation-dspy not installed")
            logger.warning("   Run: pip install openinference-instrumentation-dspy")
        except Exception as e:
            logger.error(f"❌ DSPy instrumentation failed: {e}")
        
        # Instrument LangChain (used by LangGraph in Follow-Up Agent)
        try:
            from openinference.instrumentation.langchain import LangChainInstrumentor
            
            LangChainInstrumentor().instrument()
            logger.info("✅ LangChain instrumentation enabled")
            logger.info("   LangGraph workflows (Follow-Up Agent) will be traced")
        
        except ImportError:
            logger.warning("⚠️ openinference-instrumentation-langchain not installed")
            logger.warning("   Run: pip install openinference-instrumentation-langchain")
        except Exception as e:
            logger.error(f"❌ LangChain instrumentation failed: {e}")
        
        return tracer_provider
    
    except ImportError:
        logger.error("❌ Phoenix packages not installed")
        logger.error("   Run: pip install arize-phoenix-otel openinference-instrumentation-dspy")
        return None
    
    except Exception as e:
        logger.error(f"❌ Phoenix initialization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def get_trace_url(trace_id: str, project_name: str = "hume-dspy-agent") -> str:
    """Get Phoenix UI URL for a specific trace.
    
    Args:
        trace_id: OpenTelemetry trace ID
        project_name: Phoenix project name
    
    Returns:
        URL to view trace in Phoenix UI
    """
    return f"https://app.phoenix.arize.com/projects/{project_name}/traces/{trace_id}"


# Initialize on module import (before any other code)
# This ensures tracing is active from the very start
tracer_provider = None

def setup_observability():
    """Setup function to be called explicitly from main.py"""
    global tracer_provider
    if tracer_provider is None:
        tracer_provider = initialize_phoenix_tracing()
    return tracer_provider
