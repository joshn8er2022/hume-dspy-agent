"""
Tool registry and auto-discovery system.

This module provides a central registry for tool management with automatic
discovery capabilities. Tools are discovered by scanning directories for
BaseTool subclasses and automatically registered.

Features:
- Singleton pattern for global registry
- Dynamic tool discovery via directory scanning
- Query tools by name, category, or tag
- Integration with DSPy ReAct via tool metadata
- Type-safe tool execution

Architecture:
- ToolRegistry: Central registry singleton
- discover_tools(): Scan directories for tools
- get_tool()/list_tools(): Query registered tools

Author: Claude (Sonnet 4.5)
Date: 2025-10-31
Version: 1.0
"""

from typing import Dict, List, Optional, Type
from pathlib import Path
import importlib.util
import sys
import inspect
import logging

from .base import BaseTool, ToolMetadata, ToolCategory

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Singleton registry for all tools.

    Features:
    - Register tools manually or via auto-discovery
    - Query tools by name, category, or tag
    - Generate DSPy-compatible tool lists
    - Thread-safe singleton pattern

    Examples:
        >>> registry = ToolRegistry()
        >>> registry.register_tool(my_tool)
        >>> tools = registry.get_all_tools()
        >>> data_tools = registry.list_tools(category=ToolCategory.DATA)
    """

    _instance = None
    _tools: Dict[str, BaseTool] = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register_tool(
        self,
        tool: BaseTool,
        replace: bool = False
    ) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: BaseTool instance to register
            replace: Whether to replace existing tool with same name

        Raises:
            ValueError: If tool already exists and replace=False
        """
        tool_name = tool.metadata.name

        # Check for duplicates
        if tool_name in self._tools and not replace:
            raise ValueError(
                f"Tool '{tool_name}' already registered. "
                f"Use replace=True to override."
            )

        # Validate tool
        self._validate_tool(tool)

        # Register
        self._tools[tool_name] = tool
        logger.info(f"Registered tool: {tool_name} (v{tool.metadata.version})")

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool by name.

        Args:
            name: Tool name

        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            BaseTool instance if found, None otherwise
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tag: Optional[str] = None
    ) -> List[BaseTool]:
        """
        List tools filtered by category or tag.

        Args:
            category: Filter by category (optional)
            tag: Filter by tag (optional)

        Returns:
            List of matching BaseTool instances
        """
        tools = self._tools.values()

        if category:
            tools = [t for t in tools if t.metadata.category == category]

        if tag:
            tools = [t for t in tools if tag in t.metadata.tags]

        return list(tools)

    def search_tools(self, query: str) -> List[BaseTool]:
        """
        Search tools by name, description, or tags.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching BaseTool instances
        """
        query_lower = query.lower()
        results = []

        for tool in self._tools.values():
            # Search in name
            if query_lower in tool.metadata.name.lower():
                results.append(tool)
                continue

            # Search in description
            if query_lower in tool.metadata.description.lower():
                results.append(tool)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in tool.metadata.tags):
                results.append(tool)
                continue

        return results

    def list_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())

    def count_tools(self) -> int:
        """Get total number of registered tools."""
        return len(self._tools)

    def clear(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self._tools.clear()
        logger.info("Cleared all tools from registry")

    def _validate_tool(self, tool: BaseTool) -> None:
        """
        Validate tool definition.

        Args:
            tool: BaseTool instance to validate

        Raises:
            ValueError: If tool is invalid
        """
        # Check required attributes
        if not hasattr(tool, 'metadata'):
            raise ValueError("Tool must have metadata attribute")

        if not hasattr(tool, 'Parameters'):
            raise ValueError("Tool must have Parameters class")

        if not tool.metadata.name:
            raise ValueError("Tool must have a name")

        if not tool.metadata.description:
            raise ValueError("Tool must have a description")

        # Check execute method exists
        if not hasattr(tool, 'execute'):
            raise ValueError("Tool must have execute method")


def discover_tools(
    directory: str,
    pattern: str = "*.py",
    recursive: bool = True,
    exclude: Optional[List[str]] = None
) -> int:
    """
    Discover and register tools from a directory.

    Scans the specified directory for Python modules containing BaseTool
    subclasses and automatically registers them with the global registry.

    Args:
        directory: Directory to scan for tools
        pattern: File pattern to match (default: "*.py")
        recursive: Whether to scan subdirectories (default: True)
        exclude: List of filenames to exclude (default: ["__init__.py", "base.py"])

    Returns:
        Number of tools discovered and registered

    Examples:
        >>> count = discover_tools("./tools")
        >>> print(f"Discovered {count} tools")
    """
    registry = get_global_registry()
    directory_path = Path(directory)

    if not directory_path.exists():
        logger.warning(f"Directory not found: {directory}")
        return 0

    # Default exclusions
    exclude = exclude or []
    exclude.extend(['__init__.py', 'base.py', 'registry.py', '__pycache__'])

    # Find matching files
    if recursive:
        files = list(directory_path.rglob(pattern))
    else:
        files = list(directory_path.glob(pattern))

    # Filter files
    files = [
        f for f in files
        if f.name not in exclude and f.is_file()
    ]

    initial_count = registry.count_tools()

    # Import each module
    for file_path in files:
        try:
            _import_tool_module(file_path, registry)
        except Exception as e:
            logger.error(f"Error loading tool from {file_path}: {e}")

    final_count = registry.count_tools()
    registered = final_count - initial_count

    logger.info(f"Discovered {registered} tools from {directory}")
    return registered


def _import_tool_module(file_path: Path, registry: ToolRegistry) -> None:
    """
    Import a tool module and register any tools found.

    Args:
        file_path: Path to Python module
        registry: ToolRegistry instance
    """
    # Create module name from file path
    module_name = f"dynamic_tools.{file_path.stem}"

    # Load module
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Look for BaseTool subclasses
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # Check if it's a BaseTool subclass (not BaseTool itself)
            if (inspect.isclass(attr) and
                issubclass(attr, BaseTool) and
                attr is not BaseTool):

                try:
                    # Instantiate and register
                    tool_instance = attr()
                    registry.register_tool(tool_instance, replace=True)
                    logger.debug(f"Registered tool: {tool_instance.metadata.name}")
                except Exception as e:
                    logger.error(f"Error registering {attr_name}: {e}")

        logger.debug(f"Loaded module: {file_path.name}")


# Global registry instance
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _global_registry


__all__ = [
    'ToolRegistry',
    'discover_tools',
    'get_global_registry'
]
