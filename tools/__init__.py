"""
Dynamic Tool Loading System for hume-dspy-agent.

This module provides a type-safe, discoverable tool system built on Pydantic
and designed for integration with DSPy agents.

Key Features:
- Type-safe tool definitions with Pydantic validation
- Automatic tool discovery from directories
- Centralized registry with query capabilities
- Structured execution results with error handling
- Easy integration with existing agent architecture

Quick Start:
    >>> from tools import discover_tools, get_global_registry
    >>> # Discover all tools in the tools directory
    >>> count = discover_tools("./tools")
    >>> # Get the registry
    >>> registry = get_global_registry()
    >>> # Query a specific tool
    >>> tool = registry.get_tool("supabase_lead_query")
    >>> # Execute the tool
    >>> result = await tool.run(tier="HOT", limit=10)

Author: Claude (Sonnet 4.5)
Date: 2025-10-31
Version: 1.0
"""

# Core types and base classes
from .base import (
    ToolParameterType,
    ToolCategory,
    ToolParameter,
    ToolMetadata,
    ToolError,
    ToolResult,
    BaseTool
)

# Registry and discovery
from .registry import (
    ToolRegistry,
    discover_tools,
    get_global_registry
)

# Example tools (optional - can be imported separately)
try:
    from .supabase_tools import (
        SupabaseLeadQuery,
        SupabasePipelineAnalytics
    )
    _SUPABASE_TOOLS_AVAILABLE = True
except ImportError:
    _SUPABASE_TOOLS_AVAILABLE = False

__version__ = "1.0.0"

__all__ = [
    # Core types
    'ToolParameterType',
    'ToolCategory',
    'ToolParameter',
    'ToolMetadata',
    'ToolError',
    'ToolResult',
    'BaseTool',

    # Registry
    'ToolRegistry',
    'discover_tools',
    'get_global_registry',

    # Version
    '__version__',
]

# Add supabase tools to __all__ if available
if _SUPABASE_TOOLS_AVAILABLE:
    __all__.extend([
        'SupabaseLeadQuery',
        'SupabasePipelineAnalytics'
    ])
